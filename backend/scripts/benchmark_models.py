"""
Compares candidate Ollama (or any OpenAI-compatible) models for the two roles
this app actually uses an LLM for -- chat/RAG answers and structured wiki-fact
extraction -- on speed and a cheap automatic quality proxy, and saves full
transcripts so a human can spot-check quality before picking a default.

This is the "benchmark script comparing candidate models" called for in the
LOCAL LLM STACK requirements. It goes through the same LLMGateway class every
other feature uses (app.services.llm_gateway) -- specifically its
chat_with_meta() method, which makes a live call against a *specified* model
with no mock fallback -- so there is still exactly one place in this codebase
that talks to a model server. Nothing here is wired into request-serving
code paths; it's a standalone operator tool.

Usage (from backend/, with the target Ollama reachable at OPENAI_BASE_URL):
    .venv/bin/python -m scripts.benchmark_models
    .venv/bin/python -m scripts.benchmark_models --chat-models qwen3:14b,llama3.1:8b-instruct
    .venv/bin/python -m scripts.benchmark_models --extraction-models qwen3:8b,llama3.1:8b-instruct
    .venv/bin/python -m scripts.benchmark_models --dry-run     # exercises the script with the
                                                                # mock gateway when no LLM is
                                                                # reachable; scores are not
                                                                # meaningful, just wiring-check

Writes, under scripts/benchmark_results/:
    run_<timestamp>.json   full raw per-item results (latency, tokens/sec, coverage, raw text)
    run_<timestamp>.md      human-readable per-model summary table + links to what to read next

See RESULTS_TEMPLATE.md in that same directory for the report shape and how
to interpret it, including why coverage-score is a proxy and not a verdict.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import statistics
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.ingestion import EXTRACTION_SYSTEM_PROMPT  # noqa: E402
from app.services.llm_gateway import get_gateway, safe_json_parse  # noqa: E402
from scripts.bench_fixtures import CHAT_FIXTURES, EXTRACTION_FIXTURES  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent / "benchmark_results"

DEFAULT_CHAT_MODELS = ["qwen3:14b", "llama3.1:8b-instruct"]
DEFAULT_EXTRACTION_MODELS = ["qwen3:8b", "llama3.1:8b-instruct"]

CHAT_SYSTEM_PROMPT = (
    "You are a clinical assistant answering a physician's question using ONLY the provided "
    "context block, which was retrieved from this patient's wiki and source documents. Answer "
    "concisely in 1-3 sentences. If the context doesn't support an answer, say so plainly."
)


def keyword_coverage(text: str, expected_keywords: list[str]) -> float:
    if not expected_keywords:
        return 1.0
    haystack = text.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in haystack)
    return hits / len(expected_keywords)


async def bench_chat_model(model: str, dry_run: bool) -> dict:
    gateway = get_gateway()
    items = []
    for fx in CHAT_FIXTURES:
        messages = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{fx.context}\n\nQuestion: {fx.question}"},
        ]
        try:
            if dry_run:
                content = await gateway.chat(messages, model=model)
                meta = {"content": content, "latency_seconds": None, "tokens_per_second": None}
            else:
                meta = await gateway.chat_with_meta(messages, model=model)
            score = keyword_coverage(meta["content"], fx.expected_keywords)
            items.append({"fixture_id": fx.id, "error": None, "score": score, **meta})
        except Exception as e:
            items.append(
                {"fixture_id": fx.id, "error": str(e), "score": 0.0, "content": None,
                 "latency_seconds": None, "tokens_per_second": None}
            )
    return {"model": model, "role": "chat", "items": items, **_aggregate(items)}


async def bench_extraction_model(model: str, dry_run: bool) -> dict:
    gateway = get_gateway()
    items = []
    for fx in EXTRACTION_FIXTURES:
        messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"Document type (auto-detected): {fx.doc_type}\n\nDocument text:\n{fx.text}"},
        ]
        try:
            if dry_run:
                content = await gateway.chat(messages, model=model, response_format={"type": "json_object"})
                meta = {"content": content, "latency_seconds": None, "tokens_per_second": None}
            else:
                meta = await gateway.chat_with_meta(
                    messages, model=model, response_format={"type": "json_object"}
                )
            parsed = safe_json_parse(meta["content"] or "")
            flattened = " ".join(
                fact.get("text", "")
                for facts in (parsed.get("sections") or {}).values()
                for fact in facts
            )
            score = keyword_coverage(flattened, fx.expected_keywords)
            items.append({"fixture_id": fx.id, "error": None, "score": score, "parsed_ok": bool(parsed), **meta})
        except Exception as e:
            items.append(
                {"fixture_id": fx.id, "error": str(e), "score": 0.0, "parsed_ok": False, "content": None,
                 "latency_seconds": None, "tokens_per_second": None}
            )
    return {"model": model, "role": "extraction", "items": items, **_aggregate(items)}


def _aggregate(items: list[dict]) -> dict:
    errors = sum(1 for i in items if i["error"])
    scores = [i["score"] for i in items]
    latencies = [i["latency_seconds"] for i in items if i.get("latency_seconds") is not None]
    tps = [i["tokens_per_second"] for i in items if i.get("tokens_per_second") is not None]
    return {
        "error_count": errors,
        "avg_score": round(statistics.mean(scores), 3) if scores else None,
        "avg_latency_seconds": round(statistics.mean(latencies), 2) if latencies else None,
        "avg_tokens_per_second": round(statistics.mean(tps), 1) if tps else None,
    }


def _fmt(v, suffix=""):
    return f"{v}{suffix}" if v is not None else "n/a"


def render_markdown(results: list[dict], dry_run: bool) -> str:
    lines = ["# Model benchmark results", ""]
    if dry_run:
        lines += [
            "**DRY RUN** -- no live model server was targeted; every call fell back to the "
            "gateway's mock responder, so `avg_score`/latency/tokens-per-sec below are NOT "
            "representative of any real model. Re-run without `--dry-run` against a reachable "
            "Ollama instance for real numbers.",
            "",
        ]
    lines.append(
        "`avg_score` is automatic keyword-coverage against a small hand-labeled set per "
        "fixture -- a cheap proxy, not a clinical accuracy measurement. Read the transcripts in "
        "the accompanying `.json` for any model you're seriously considering before choosing it."
    )
    lines.append("")
    for role in ("chat", "extraction"):
        role_results = [r for r in results if r["role"] == role]
        if not role_results:
            continue
        lines.append(f"## {role.capitalize()} models")
        lines.append("")
        lines.append("| model | avg score | avg latency (s) | avg tokens/sec | errors |")
        lines.append("|---|---|---|---|---|")
        for r in role_results:
            lines.append(
                f"| {r['model']} | {_fmt(r['avg_score'])} | {_fmt(r['avg_latency_seconds'])} | "
                f"{_fmt(r['avg_tokens_per_second'])} | {r['error_count']}/{len(r['items'])} |"
            )
        lines.append("")
    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--chat-models", default=",".join(DEFAULT_CHAT_MODELS))
    parser.add_argument("--extraction-models", default=",".join(DEFAULT_EXTRACTION_MODELS))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use the gateway's mock fallback instead of a live model server (wiring check only, "
        "scores are not meaningful).",
    )
    args = parser.parse_args()

    chat_models = [m.strip() for m in args.chat_models.split(",") if m.strip()]
    extraction_models = [m.strip() for m in args.extraction_models.split(",") if m.strip()]

    print(f"Benchmarking chat models: {chat_models}")
    print(f"Benchmarking extraction models: {extraction_models}")
    if args.dry_run:
        print("--dry-run set: using mock responses, scores/timings are NOT meaningful.\n")

    results = []
    for model in chat_models:
        print(f"  chat  :: {model} ...")
        results.append(await bench_chat_model(model, args.dry_run))
    for model in extraction_models:
        print(f"  extract :: {model} ...")
        results.append(await bench_extraction_model(model, args.dry_run))

    await get_gateway().aclose()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = RESULTS_DIR / f"run_{ts}.json"
    md_path = RESULTS_DIR / f"run_{ts}.md"

    json_path.write_text(json.dumps({"dry_run": args.dry_run, "generated_at": ts, "results": results}, indent=2))
    md_path.write_text(render_markdown(results, args.dry_run))

    print(f"\nWrote {json_path}")
    print(f"Wrote {md_path}")
    print()
    print(render_markdown(results, args.dry_run))


if __name__ == "__main__":
    asyncio.run(main())
