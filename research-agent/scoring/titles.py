"""Six-level title hierarchy shared by the scorers (ported from sierra-demo)."""

from __future__ import annotations

import re


_FOUNDER_RE = re.compile(r"\b(co[-\s]?founder|founder)\b", re.I)


def classify_title(title: str | None, include_founder: bool = False) -> int | None:
    if not title:
        return None
    t = f" {title.lower().replace('/', ' ')} "

    if include_founder and _FOUNDER_RE.search(t):
        return 6
    if not include_founder and _FOUNDER_RE.search(t):
        return None

    if re.search(r"\b(ceo|cto|cfo|coo|cmo|cpo)\b", t):
        return 6
    if "chief " in t or "general partner" in t:
        return 6

    if re.search(r"\b(svp|evp|vp)\b", t) or "vice president" in t:
        return 5
    if "head of" in t or re.search(r"\bpartner\b", t):
        return 5

    # Senior IC titles that contain "fellow" or "engineer" but are peer-with-VP.
    # Disambiguated before the level-2 keyword catch.
    if "technical fellow" in t or "distinguished fellow" in t or "distinguished engineer" in t:
        return 5

    if "director" in t or "principal" in t:
        return 4

    if any(word in t for word in ("senior", "staff", "lead", "manager", "sr.")):
        return 3

    if any(word in t for word in ("engineer", "developer", "designer", "scientist", "analyst", "researcher", "fellow")):
        return 2

    if any(word in t for word in ("intern", "associate", "junior", "coordinator", "jr.")):
        return 1

    return None
