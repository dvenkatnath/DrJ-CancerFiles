# How to read (and produce) a benchmark run

Each run of `python -m scripts.benchmark_models` writes two files here, named
by UTC timestamp:

- `run_<timestamp>.md` -- the human-readable summary table below, generated automatically.
- `run_<timestamp>.json` -- full raw data: every fixture's prompt, the model's raw response text,
  latency, tokens/sec, and the automatic score, for every candidate model. Read this before
  trusting the summary table for any model you're seriously considering -- the score is a cheap
  keyword-coverage proxy (see `scripts/bench_fixtures.py`'s module docstring), not a substitute for
  a clinician spot-checking a handful of real transcripts.

## Running it for real

The script needs a reachable Ollama (or other OpenAI-compatible server) at `OPENAI_BASE_URL`, with
every candidate model already pulled (`ollama pull qwen3:14b`, etc.):

```bash
cd backend
.venv/bin/python -m scripts.benchmark_models \
  --chat-models qwen3:14b,llama3.1:8b-instruct \
  --extraction-models qwen3:8b,llama3.1:8b-instruct
```

Defaults match the models named in the deployment spec (`qwen3:14b` for chat, `qwen3:8b` /
`llama3.1:8b-instruct` for extraction) if you omit the flags. Add `--dry-run` to exercise the
script's wiring with the mock gateway when no LLM is reachable -- useful for confirming the script
itself still works after an edit, but the scores/timings from a dry run are meaningless and the
report says so at the top.

Embeddings (`nomic-embed-text` vs `bge-m3`) aren't benchmarked here for speed/quality in the same
way, since there's no cheap automatic proxy for embedding quality without a labeled retrieval set --
compare them instead by seeding the same documents under each and eyeballing whether
`Ask` returns the passages you'd expect for a handful of real questions.

## Example shape (from a `--dry-run`, so scores are not meaningful -- included only to show the report format)

# Model benchmark results

**DRY RUN** -- no live model server was targeted; every call fell back to the gateway's mock
responder, so `avg_score`/latency/tokens-per-sec below are NOT representative of any real model.
Re-run without `--dry-run` against a reachable Ollama instance for real numbers.

`avg_score` is automatic keyword-coverage against a small hand-labeled set per fixture -- a cheap
proxy, not a clinical accuracy measurement. Read the transcripts in the accompanying `.json` for
any model you're seriously considering before choosing it.

## Chat models

| model | avg score | avg latency (s) | avg tokens/sec | errors |
|---|---|---|---|---|
| qwen3:14b | 1.0 | n/a | n/a | 0/10 |

## Extraction models

| model | avg score | avg latency (s) | avg tokens/sec | errors |
|---|---|---|---|---|
| qwen3:8b | 0.0 | n/a | n/a | 0/10 |

## Choosing a default

Update `CHAT_MODEL` / `EXTRACTION_MODEL` / `EMBEDDING_MODEL` in `.env` (read by
`app/config.py`, consumed everywhere through `app/services/llm_gateway.py`) -- that's the
only place these choices live, so switching the default after benchmarking is a config
change, not a code change, exactly like switching deployment targets.
