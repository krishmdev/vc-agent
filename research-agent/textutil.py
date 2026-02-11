"""Small lexical helpers used by the offline (no-LLM) code paths."""

import re

STOPWORDS = frozenset(
    """a an and are as at be been but by can could did do does doing for from had has have how i if
    in into is it its just like me my of on or our so than that the their them then there these they
    this to up us was we were what when where which who why will with would you your yours about
    should any also more most much very really get got make made one ok okay yeah know think going""".split()
)

_WORD = re.compile(r"[a-z0-9$%][a-z0-9$%'\-]*")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


def tokens(text: str) -> list[str]:
    return [t for t in _WORD.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]


def overlap_score(query_tokens: set[str], text: str) -> float:
    toks = tokens(text)
    if not toks or not query_tokens:
        return 0.0
    hits = sum(1 for t in toks if t in query_tokens)
    distinct = len(query_tokens & set(toks))
    # Distinct matches matter most; raw hit density breaks ties without rewarding long text.
    return distinct + hits / (len(toks) + 5)


def sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def best_sentences(
    query: str, text: str, *, k: int = 2, min_len: int = 50, max_len: int = 320
) -> list[str]:
    q = set(tokens(query))
    candidates = [s for s in sentences(text) if min_len <= len(s) <= max_len]
    ranked = sorted(candidates, key=lambda s: overlap_score(q, s), reverse=True)
    return ranked[:k]


def jaccard(a: str, b: str) -> float:
    ta, tb = set(tokens(a)), set(tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)
