"""Ollama client for Arriella Grapevine (vision + text)."""

from __future__ import annotations

import json
from typing import Any, Optional

import requests

from infobroker.config import get_settings

DEFAULT_MODEL = "arriella-grapevine:latest"


def ollama_base() -> str:
    import os

    return os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")


def grapevine_model() -> str:
    import os

    return os.getenv("INFOBROKER_OLLAMA_MODEL", DEFAULT_MODEL)


def ollama_healthy() -> dict[str, Any]:
    try:
        resp = requests.get(f"{ollama_base()}/api/version", timeout=3)
        resp.raise_for_status()
        tags = requests.get(f"{ollama_base()}/api/tags", timeout=5)
        names = [m.get("name") for m in (tags.json().get("models") or [])]
        model = grapevine_model()
        return {
            "ok": True,
            "version": resp.json().get("version"),
            "model": model,
            "model_present": model in names or any(model.split(":")[0] in (n or "") for n in names),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "model": grapevine_model()}


def chat(
    messages: list[dict[str, Any]],
    *,
    images_b64: Optional[list[str]] = None,
    temperature: float = 0.2,
    timeout: int = 120,
) -> str:
    """Chat with Grapevine. Attach images to the last user message when provided."""
    payload_messages = []
    for i, msg in enumerate(messages):
        item = {"role": msg["role"], "content": msg.get("content") or ""}
        if images_b64 and i == len(messages) - 1 and msg["role"] == "user":
            item["images"] = images_b64
        payload_messages.append(item)

    resp = requests.post(
        f"{ollama_base()}/api/chat",
        json={
            "model": grapevine_model(),
            "messages": payload_messages,
            "stream": False,
            "options": {"temperature": temperature},
        },
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Ollama error {resp.status_code}: {resp.text[:400]}")
    data = resp.json()
    return (data.get("message") or {}).get("content") or ""
