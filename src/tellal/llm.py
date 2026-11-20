"""Optional language model: any OpenAI-compatible chat endpoint (Ollama, LM Studio, OpenAI, OpenRouter...).

Tellal works fully without it. When it is configured and answers, captions are written by the model;
when it does not answer, the template engine is used and nothing breaks.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx

_down_until = 0.0


def make_chat(settings, transport: httpx.BaseTransport | None = None):  # noqa: ANN001, ANN201
    """Returns chat(system, user_obj) -> dict | None, or None if the LLM is turned off."""
    if not settings.llm_enabled:
        return None

    def chat(system: str, user: Any) -> dict[str, Any] | None:
        global _down_until
        if time.time() < _down_until:
            return None
        try:
            with httpx.Client(timeout=60, transport=transport) as c:
                r = c.post(
                    f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json={
                        "model": settings.llm_model,
                        "temperature": 0.8,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
                        ],
                    },
                )
                r.raise_for_status()
                text = r.json()["choices"][0]["message"]["content"]
        except Exception:  # noqa: BLE001 - unreachable, wrong model, bad JSON: fall back to templates
            _down_until = time.time() + 120
            return None
        return parse_json(text)

    return chat


def parse_json(text: str) -> dict[str, Any] | None:
    text = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.M).strip()
    try:
        v = json.loads(text)
    except ValueError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return None
        try:
            v = json.loads(m.group(0))
        except ValueError:
            return None
    return v if isinstance(v, dict) else None
