"""Shared text normalization for deterministic command matching."""

from __future__ import annotations

import re


def normalize(text: str) -> str:
    text = text.casefold().strip()
    text = re.sub(r"[^\w\s']", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(?:^|\s)(?:archi|archie)\s+stop$", "", text).strip()
    for assistant_name in ("archi", "archie"):
        if text == assistant_name:
            return ""
        if text.startswith(f"{assistant_name} "):
            text = text[len(assistant_name):].strip()
            break
    for prefix in ("please ", "can you ", "could you ", "would you ", "will you "):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    return text
