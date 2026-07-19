"""Build multi-page lesson payloads from base lessons + insight pages."""

from __future__ import annotations

from typing import Any

from infobroker.education.insights import EXTRA_PAGES


def build_pages(lesson: dict[str, Any]) -> list[dict[str, Any]]:
    """Split a classic lesson dict into teachable pages."""
    pages: list[dict[str, Any]] = []
    chart = lesson.get("chart") or {}

    pages.append(
        {
            "title": "Overview",
            "insight": (lesson.get("overview") or lesson.get("body") or "")[:280],
            "sections": [
                {
                    "heading": lesson.get("title", "Lesson"),
                    "text": lesson.get("overview") or lesson.get("body") or "",
                }
            ],
            "chart": chart,
            "topics": lesson.get("topics") or [],
        }
    )

    sections = list(lesson.get("sections") or [])
    for i in range(0, len(sections), 2):
        chunk = sections[i : i + 2]
        pages.append(
            {
                "title": chunk[0]["heading"] if chunk else f"Part {i // 2 + 2}",
                "insight": _first_sentence(chunk[0]["text"]) if chunk else "",
                "sections": chunk,
                "chart": chart if i == 0 else None,
            }
        )

    if lesson.get("terms") or lesson.get("examples"):
        pages.append(
            {
                "title": "Language & examples",
                "insight": "Own the vocabulary, then study how it shows up in real tape.",
                "terms": lesson.get("terms") or [],
                "examples": lesson.get("examples") or [],
                "chart": chart,
            }
        )

    if lesson.get("takeaways") or lesson.get("practice"):
        pages.append(
            {
                "title": "Drill it on the desk",
                "insight": "Reading without reps is entertainment. Use the buttons below.",
                "takeaways": lesson.get("takeaways") or [],
                "practice": lesson.get("practice") or [],
                "chart": {"type": "playbook_demo", "caption": "Practice loop on Infobroker."},
            }
        )

    for extra in EXTRA_PAGES.get(lesson.get("id") or "", []):
        pages.append(extra)

    # Ensure every page has a stable index label
    for idx, p in enumerate(pages):
        p["index"] = idx
        p["label"] = f"{idx + 1}/{len(pages)}"
    return pages


def attach_pages(lesson: dict[str, Any]) -> dict[str, Any]:
    out = dict(lesson)
    if out.get("pages"):
        pages = list(out["pages"])
        for idx, p in enumerate(pages):
            p = dict(p)
            p["index"] = idx
            p["label"] = f"{idx + 1}/{len(pages)}"
            pages[idx] = p
        out["pages"] = pages
    else:
        out["pages"] = build_pages(out)
    out["page_count"] = len(out["pages"])
    return out


def _first_sentence(text: str) -> str:
    text = (text or "").strip()
    for sep in (". ", "? ", "! "):
        if sep in text:
            return text.split(sep)[0] + sep.strip()
    return text[:200]
