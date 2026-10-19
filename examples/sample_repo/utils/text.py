"""Text utilities."""
from __future__ import annotations

import re

_WS = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Convert a string into a URL-friendly slug."""
    return _WS.sub("-", value.strip().lower()).strip("-")


def normalize(value: str) -> str:
    """Collapse internal whitespace."""
    return " ".join(value.split())
