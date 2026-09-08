"""
Retrieval-augmented generation for the Ask (chat) tab, scoped strictly to one
patient's own wiki + documents. Keeps chat context small (top-k chunks + the
current wiki, not the whole record) per the accuracy/speed tactics in the
design brief.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from sqlalchemy import text as sqltext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.document import Document, DocumentStatus
from app.models.wiki import WikiSection
from app.services.llm_gateway import get_gateway

settings = get_settings()

SYSTEM_PROMPT = """You are a clinical assistant embedded in a physician-facing chart review tool.
Answer the question ONLY using the patient context supplied below (their living wiki summary and
retrieved document excerpts). Every claim must be grounded in that context.
If the answer isn't present in the given context, say so plainly rather than guessing or using
outside medical knowledge. Be concise and clinical, not conversational filler."""


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


async def retrieve_chunks(db: Session, patient_id: uuid.UUID, question: str, k: int = 6) -> list[dict]:
    gateway = get_gateway()
    q_embedding = (await gateway.embed([question]))[0]
    rows = db.execute(
        sqltext(
            """
            SELECT dc.id, dc.document_id, dc.text, dc.page, dc.section_label,
                   d.filename, d.status,
                   1 - (dc.embedding <=> CAST(:qemb AS vector)) AS score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.patient_id = :pid AND dc.embedding IS NOT NULL
            ORDER BY dc.embedding <=> CAST(:qemb AS vector)
            LIMIT :k
            """
        ),
        {"qemb": _vector_literal(q_embedding), "pid": str(patient_id), "k": k},
    ).mappings().all()
    return [dict(r) for r in rows]


def wiki_context_block(db: Session, patient_id: uuid.UUID) -> tuple[str, bool]:
    sections = db.query(WikiSection).filter(WikiSection.patient_id == patient_id).all()
    lines = []
    any_unreviewed = False
    for s in sections:
        facts = s.content or []
        if not facts:
            continue
        lines.append(f"## {s.section_type.value.replace('_', ' ').title()}")
        for f in facts:
            if isinstance(f, dict):
                status = f.get("status", "reviewed")
                if status == "unreviewed":
                    any_unreviewed = True
                lines.append(f"- {f.get('text', '')}" + (" (unreviewed AI draft)" if status == "unreviewed" else ""))
    return ("\n".join(lines) or "(wiki is empty -- no documents curated yet)"), any_unreviewed


def _mock_rag_answer(question: str, chunks: list[dict], wiki_block: str) -> str:
    q_words = {w for w in question.lower().split() if len(w) > 3}
    best = None
    best_score = -1
    for c in chunks:
        overlap = sum(1 for w in q_words if w in c["text"].lower())
        if overlap > best_score:
            best_score, best = overlap, c
    if best and best_score > 0:
        snippet = " ".join(best["text"].split())[:280]
        return (
            f"_(mock model -- no LLM reachable)_\n\nBased on **{best['filename']}**, the closest matching "
            f"passage is:\n\n> {snippet}\n\nThis is a keyword-matched excerpt, not a generated summary -- "
            f"configure a reachable Ollama gateway for a synthesized answer."
        )
    if chunks:
        snippet = " ".join(chunks[0]["text"].split())[:280]
        return (
            f"_(mock model -- no LLM reachable)_\n\nI couldn't find a strong keyword match, but here is the "
            f"top-retrieved passage from **{chunks[0]['filename']}**:\n\n> {snippet}"
        )
    return (
        "_(mock model -- no LLM reachable)_\n\nNothing in this patient's curated records or documents "
        "matches this question yet."
    )


async def stream_answer(
    db: Session, patient_id: uuid.UUID, question: str, history: list[dict]
) -> tuple[AsyncIterator[str], list[dict], bool]:
    """Returns (token_stream, citations, pending_curation_flag). Citations and
    the flag are computed up front (before streaming starts) since they depend
    only on retrieval, not on the model's generated text."""
    chunks = await retrieve_chunks(db, patient_id, question)
    wiki_block, wiki_has_unreviewed = wiki_context_block(db, patient_id)

    citations = [
        {
            "document_id": str(c["document_id"]),
            "chunk_id": str(c["id"]),
            "document_name": c["filename"],
            "page": c["page"],
            "section_label": c["section_label"],
            "snippet": " ".join(c["text"].split())[:240],
        }
        for c in chunks
    ]
    pending_flag = wiki_has_unreviewed or any(
        c["status"] not in (DocumentStatus.curated.value,) for c in chunks
    )

    context_block = (
        f"# Patient wiki (curated summary)\n{wiki_block}\n\n"
        f"# Retrieved document excerpts\n"
        + "\n\n".join(f"[{i+1}] ({c['filename']}): {' '.join(c['text'].split())[:600]}" for i, c in enumerate(chunks))
    )

    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "system", "content": context_block}]
        + history
        + [{"role": "user", "content": question}]
    )

    gateway = get_gateway()
    stream = gateway.chat_stream(
        messages,
        model=settings.chat_model,
        mock_fn=lambda _msgs: _mock_rag_answer(question, chunks, wiki_block),
    )
    return stream, citations, pending_flag
