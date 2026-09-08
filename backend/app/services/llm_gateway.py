"""
The internal LLM gateway. This is the ONLY module in this codebase allowed to
make a network call to a language model. Every feature (extraction, chat,
embeddings) goes through the functions here, which in turn read only
OPENAI_BASE_URL + *_MODEL from app.config.

This is what makes "switch deployment target = config change, zero code
change" true:
  DEV           OPENAI_BASE_URL=http://localhost:11434/v1        (Ollama, Mac Mini)
  RAILWAY POC   OPENAI_BASE_URL=https://<tunnel>/v1               (Ollama via Cloudflare
                                                                    Tunnel/ngrok, or any
                                                                    OpenAI-compatible host
                                                                    of open-weights models
                                                                    -- synthetic data only)
  CLIENT        OPENAI_BASE_URL=http://<onprem-host>:11434/v1     (on-prem Ollama; PHI
                                                                    never leaves this network)

No provider SDK (openai-python, anthropic, etc.) is imported anywhere in this
codebase, here included -- only httpx against the OpenAI-compatible surface
that Ollama (and most open-weights servers) exposes.

Accuracy/speed tactics implemented here per the design brief: streaming
responses, retry with backoff, an explicit model-unavailable state, and a full
mock mode so the rest of the app runs end-to-end with zero LLM reachable.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import time
from collections.abc import AsyncIterator, Callable
from typing import Any, Literal

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = logging.getLogger("llm_gateway")

RETRYABLE_EXC = (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.ConnectTimeout)

GatewayMode = Literal["live", "mock", "mock_fallback"]


class LLMUnavailableError(RuntimeError):
    """Raised when LLM_MODE=live and the gateway cannot be reached after retries."""


class _GatewayHealth:
    """Cached reachability probe so every request doesn't re-check the gateway."""

    def __init__(self, ttl_seconds: float = 15.0):
        self._ttl = ttl_seconds
        self._checked_at = 0.0
        self._reachable = False

    async def is_reachable(self, client: httpx.AsyncClient) -> bool:
        now = time.monotonic()
        if now - self._checked_at < self._ttl:
            return self._reachable
        try:
            resp = await client.get("/models", timeout=3.0)
            self._reachable = resp.status_code < 500
        except Exception:
            self._reachable = False
        self._checked_at = now
        return self._reachable

    def invalidate(self) -> None:
        self._checked_at = 0.0


class LLMGateway:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = httpx.AsyncClient(
            base_url=self.settings.openai_base_url,
            headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
            timeout=httpx.Timeout(self.settings.llm_request_timeout_seconds),
        )
        self._health = _GatewayHealth()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def mode(self) -> GatewayMode:
        if self.settings.llm_mode == "mock":
            return "mock"
        reachable = await self._health.is_reachable(self._client)
        if reachable:
            return "live"
        if self.settings.llm_mode == "live":
            raise LLMUnavailableError(
                f"LLM gateway at {self.settings.openai_base_url} is unreachable and LLM_MODE=live"
            )
        return "mock_fallback"  # LLM_MODE=auto, gateway down -> degrade gracefully

    async def health(self) -> dict[str, Any]:
        try:
            mode: str = await self.mode()
            unavailable = False
        except LLMUnavailableError:
            mode = "unavailable"
            unavailable = True
        return {
            "mode": mode,
            "unavailable": unavailable,
            "base_url": self.settings.openai_base_url,
            "chat_model": self.settings.chat_model,
            "extraction_model": self.settings.extraction_model,
            "embedding_model": self.settings.embedding_model,
        }

    # ------------------------------------------------------------------ chat
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        response_format: dict | None = None,
        mock_fn: Callable[[list[dict[str, str]]], str] | None = None,
    ) -> str:
        """Non-streaming chat completion. Falls back to a mock responder if the
        gateway is unreachable (LLM_MODE=auto) or mocked outright."""
        mode = await self.mode()
        if mode in ("mock", "mock_fallback"):
            return (mock_fn or _default_mock_chat)(messages)

        try:
            return await self._chat_call(messages, model, temperature, response_format)
        except Exception as e:
            logger.warning("LLM chat call failed after retries, falling back to mock: %s", e)
            self._health.invalidate()
            return (mock_fn or _default_mock_chat)(messages)

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.1,
        mock_fn: Callable[[list[dict[str, str]]], dict] | None = None,
    ) -> dict:
        """Schema-ish constrained output: asks for a JSON object and defensively
        parses the result (models occasionally wrap it in prose/code fences)."""
        if mock_fn is not None:
            mode = await self.mode()
            if mode in ("mock", "mock_fallback"):
                return mock_fn(messages)

        text = await self.chat(
            messages,
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
            mock_fn=(lambda m: json.dumps(mock_fn(m))) if mock_fn else None,
        )
        return _safe_json_parse(text)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=8),
        retry=retry_if_exception_type(RETRYABLE_EXC),
    )
    async def _chat_call(
        self,
        messages: list[dict[str, str]],
        model: str | None,
        temperature: float,
        response_format: dict | None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model or self.settings.chat_model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
            "keep_alive": self.settings.llm_keep_alive,
        }
        if response_format:
            payload["response_format"] = response_format
        resp = await self._client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def chat_with_meta(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float = 0.2,
        response_format: dict | None = None,
    ) -> dict[str, Any]:
        """Like chat(), but always makes a live call against the given `model`
        with NO mock fallback and no reachability short-circuit, and returns
        timing/token metadata alongside the text.

        This exists solely for scripts/benchmark_models.py, which needs to
        compare several candidate models against each other (as opposed to
        every other call site, which always targets the single configured
        chat/extraction model). It still goes through this one gateway class
        and the same OpenAI-compatible /chat/completions surface -- no
        provider SDK, no other network call site.
        """
        start = time.monotonic()
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
            "keep_alive": self.settings.llm_keep_alive,
        }
        if response_format:
            payload["response_format"] = response_format
        resp = await self._client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        elapsed = time.monotonic() - start
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage") or {}
        completion_tokens = usage.get("completion_tokens")
        tokens_per_second = (completion_tokens / elapsed) if completion_tokens and elapsed > 0 else None
        return {
            "content": content,
            "latency_seconds": elapsed,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": completion_tokens,
            "tokens_per_second": tokens_per_second,
        }

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        mock_fn: Callable[[list[dict[str, str]]], str] | None = None,
    ) -> AsyncIterator[str]:
        """Yields incremental text chunks (SSE `delta.content`). Falls back to
        yielding the mock response chunk-by-chunk so the frontend's streaming UI
        works identically in mock mode."""
        mode = await self.mode()
        if mode in ("mock", "mock_fallback"):
            async for chunk in _stream_text((mock_fn or _default_mock_chat)(messages)):
                yield chunk
            return

        payload = {
            "model": model or self.settings.chat_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            "keep_alive": self.settings.llm_keep_alive,
        }
        try:
            async with self._client.stream("POST", "/chat/completions", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0]["delta"].get("content")
                    except Exception:
                        continue
                    if delta:
                        yield delta
        except Exception as e:
            logger.warning("LLM stream call failed, falling back to mock: %s", e)
            self._health.invalidate()
            async for chunk in _stream_text((mock_fn or _default_mock_chat)(messages)):
                yield chunk

    # ------------------------------------------------------------- embeddings
    async def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        mode = await self.mode()
        if mode in ("mock", "mock_fallback"):
            return [_mock_embedding(t, self.settings.embedding_dim) for t in texts]
        try:
            return await self._embed_call(texts, model)
        except Exception as e:
            logger.warning("Embeddings call failed after retries, falling back to mock: %s", e)
            self._health.invalidate()
            return [_mock_embedding(t, self.settings.embedding_dim) for t in texts]

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=8),
        retry=retry_if_exception_type(RETRYABLE_EXC),
    )
    async def _embed_call(self, texts: list[str], model: str | None) -> list[list[float]]:
        resp = await self._client.post(
            "/embeddings", json={"model": model or self.settings.embedding_model, "input": texts}
        )
        resp.raise_for_status()
        data = resp.json()
        return [row["embedding"] for row in data["data"]]


async def _stream_text(text: str, chunk_size: int = 24) -> AsyncIterator[str]:
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]
        await asyncio.sleep(0.015)


def _default_mock_chat(messages: list[dict[str, str]]) -> str:
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    return (
        "_(mock model -- no LLM reachable at the configured gateway)_\n\n"
        f"I can't reach a language model right now, so this is an offline placeholder "
        f"response for: “{last_user[:200]}”"
    )


def _mock_embedding(text: str, dim: int) -> list[float]:
    """
    Deterministic, dependency-free stand-in for a real embedding model: hashed
    bag-of-words feature hashing into `dim` buckets, L2-normalized. Not
    semantically meaningful the way a trained embedding model is, but it IS
    lexically consistent -- documents sharing vocabulary land closer together --
    so pgvector cosine search over these mock vectors still behaves sensibly
    for demo/mock mode instead of returning pure noise.
    """
    vec = [0.0] * dim
    for word in text.lower().split():
        h = int(hashlib.sha256(word.encode()).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h // dim) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def safe_json_parse(text: str) -> dict:
    """Public alias of the defensive JSON-object parser used internally by
    chat_json(), so other trusted call sites in this codebase (currently just
    scripts/benchmark_models.py) can reuse the same tolerant parsing instead of
    duplicating it, without reaching into a private name."""
    return _safe_json_parse(text)


def _safe_json_parse(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        logger.error("Could not parse JSON from model output (first 500 chars): %r", text[:500])
        return {}


_gateway_singleton: LLMGateway | None = None


def get_gateway() -> LLMGateway:
    global _gateway_singleton
    if _gateway_singleton is None:
        _gateway_singleton = LLMGateway()
    return _gateway_singleton
