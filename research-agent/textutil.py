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


_MARKUP = re.compile(r">>|^#+\s*|\*\*|__|\[(?:Music|Applause|Laughter)\]", re.MULTILINE | re.IGNORECASE)


def sentences(text: str) -> list[str]:
    # Transcripts carry caption speaker marks (">>") and articles carry markdown; neither reads
    # well inside a quote.
    text = _MARKUP.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def best_sentences(
    query: str, text: str, *, k: int = 2, min_len: int = 50, max_len: int = 320
) -> list[str]:
    q = set(tokens(query))
    candidates = [s for s in sentences(text) if min_len <= len(s) <= max_len]
    scored = [(overlap_score(q, s), s) for s in candidates]
    ranked = sorted((pair for pair in scored if pair[0] > 0), key=lambda pair: pair[0], reverse=True)
    return [s for _, s in ranked[:k]]


def jaccard(a: str, b: str) -> float:
    ta, tb = set(tokens(a)), set(tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)
