"""
Lab-value trend aggregation for the "Lab Trends" panel on the Summary page.

Reads a patient's published `lab_highlights` WikiSection.content (which
accumulates one fact per accepted/edited curation section forever --
see curation_service.publish_curation) and groups whichever facts carry
structured `test`/`value` fields (set at extraction time -- see
ingestion.py's normalize_lab_marker and EXTRACTION_SYSTEM_PROMPT) into a
per-marker time series with a computed direction.

This is deliberately generic rather than hand-built per patient: the earlier
single-patient dashboard prototype (`_Dashboard/scripts/build_wiki_*.py`)
hand-transcribed each patient's CA-125/CEA/etc. trend into a hardcoded Python
list. Here, any patient whose curator has accepted enough structured lab
facts gets the same trend charts for free, from whatever markers actually
appear in their records -- not a fixed list picked in advance.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.wiki import WikiSection, WikiSectionType

# >10% change between the two most recent readings counts as a real move;
# smaller drift is reported as "stable" rather than noise.
TREND_THRESHOLD = 0.10


def compute_lab_trends(db: Session, patient_id: uuid.UUID) -> list[dict]:
    section = (
        db.query(WikiSection)
        .filter(WikiSection.patient_id == patient_id, WikiSection.section_type == WikiSectionType.lab_highlights)
        .first()
    )
    if section is None:
        return []

    series: dict[str, list[dict]] = {}
    for fact in section.content or []:
        test = fact.get("test")
        value = fact.get("value")
        # Only published (reviewed) facts feed the trend -- an AI draft still
        # sitting unreviewed in the curation queue hasn't been confirmed yet.
        if not test or value is None or fact.get("status") == "unreviewed":
            continue
        series.setdefault(test, []).append(
            {
                "date": fact.get("event_date"),
                "value": float(value),
                "unit": fact.get("unit"),
                "document_id": (fact.get("sources") or [{}])[0].get("document_id"),
                "fact_id": fact.get("id"),
            }
        )

    markers: list[dict] = []
    for test, points in series.items():
        # Undated points sort last so a missing date can't masquerade as the
        # most recent reading and skew the computed direction.
        ordered = sorted(points, key=lambda p: (p["date"] is None, p["date"] or ""))
        deduped: list[dict] = []
        seen: set[tuple] = set()
        for p in ordered:
            key = (p["date"], p["value"])
            if key in seen:
                # Same result re-mentioned in another document (very common --
                # a follow-up note often restates the last lab value).
                continue
            seen.add(key)
            deduped.append(p)
        if not deduped:
            continue

        direction = "insufficient_data"
        if len(deduped) >= 2:
            prev, last = deduped[-2]["value"], deduped[-1]["value"]
            if prev == 0:
                direction = "rising" if last > 0 else "stable"
            else:
                pct_change = (last - prev) / abs(prev)
                if pct_change > TREND_THRESHOLD:
                    direction = "rising"
                elif pct_change < -TREND_THRESHOLD:
                    direction = "falling"
                else:
                    direction = "stable"

        markers.append(
            {
                "test": test,
                "unit": deduped[-1].get("unit"),
                "points": deduped,
                "direction": direction,
                "latest_value": deduped[-1]["value"],
                "latest_date": deduped[-1]["date"],
            }
        )

    markers.sort(key=lambda m: m["test"])
    return markers
