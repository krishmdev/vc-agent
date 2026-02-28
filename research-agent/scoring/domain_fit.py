"""Domain Fit (0-30): is the founder building in a domain that matches their background?

Ported from sierra-demo's domain_fit_scorer. The comparator (seven match tiers from perfect
subdomain match down to adjacent domains, a keyword-Jaccard adjustment, and the floor for a
current operator at a thinly described company) is unchanged. The tags come from a
DomainClassifier (classifier.py), run before scoring, so this module has no I/O.

Company evidence: sierra-demo graded Form D, website and PDL sources. Here the only source is
what the founder tells us, so a description of 8+ words counts as "medium", an industry or a
short description as "weak", and a bare name as "name_only".
"""

from __future__ import annotations

import json
import re
from functools import cache

from .classifier import DATA_DIR, taxonomy
from .profile import get_company_name, get_experience, get_title

TOKEN_RE = re.compile(r"[a-z0-9]+")
OPERATOR_TITLE_RE = re.compile(
    r"\b(founder|co[- ]?founder|cofounder|chief executive|ceo|chief technology|cto)\b",
    re.I,
)
LEGAL_SUFFIXES = {
    "inc", "incorporated", "corp", "corporation", "co", "company", "llc",
    "ltd", "limited", "plc", "holdings", "holding",
}


@cache
def synonyms() -> dict:
    return json.loads((DATA_DIR / "keyword_synonyms.json").read_text())


def company_evidence_level(company: dict) -> str:
    description = str(company.get("description") or "")
    if len(description.split()) >= 8:
        return "medium"
    if description.strip() or str(company.get("industry") or "").strip():
        return "weak"
    return "name_only"


class DomainFitScorer:
    def score(self, profile: dict, company: dict | None, founder_tags: dict, company_tags: dict) -> dict:
        if not company:
            return {"domain_fit_score": 0, "breakdown": self._empty_breakdown()}
        filing = {"entity_name": company.get("name") or ""}
        evidence_level = company_evidence_level(company)
        compared = self.compare(founder_tags, company_tags)
        self._apply_weak_company_fallback(compared, founder_tags, company_tags, evidence_level, profile, filing)
        compared["company_evidence_level"] = evidence_level
        compared["founder_tags"] = founder_tags
        compared["company_tags"] = company_tags
        return {"domain_fit_score": compared["final_score"], "breakdown": compared}

    def compare(self, founder_tags: dict, company_tags: dict) -> dict:
        base, match_type = self._base_score(founder_tags, company_tags)
        founder_keywords = founder_tags.get("keywords") or []
        company_keywords = company_tags.get("keywords") or []
        jaccard, shared_tokens = self._keyword_jaccard(founder_keywords, company_keywords)

        # Floor: one side classified as 'other' but the other has a real
        # primary domain still carries partial signal — give it 3 base pts so
        # keyword overlap can pull it higher.
        f_primary = founder_tags.get("primary_domain")
        c_primary = company_tags.get("primary_domain")
        one_sided_other = (f_primary == "other") != (c_primary == "other")
        if base == 0 and one_sided_other:
            base = 3
            match_type = "one_sided_other_floor"

        adjustment = 0
        if base == 0:
            adjustment = 0
        elif jaccard >= 0.30:
            adjustment = 3
        elif jaccard >= 0.20:
            adjustment = 2
        elif jaccard >= 0.10:
            adjustment = 1
        elif founder_keywords and company_keywords and jaccard < 0.02 and base >= 30:
            # Only penalize "perfect match with completely disjoint keywords."
            # Gemini-generated keywords are noisy; the prior -3 penalty fired
            # for 17.6% of founders, often unfairly.
            adjustment = -2
        final = max(0, min(30, base + adjustment))
        return {
            "base_score": base,
            "adjustment": adjustment,
            "final_score": final,
            "match_type": match_type,
            "keyword_jaccard": round(jaccard, 3),
            "shared_keywords": shared_tokens,
        }

    def _base_score(self, founder: dict, company: dict) -> tuple[int, str]:
        f_primary_pair = (founder.get("primary_domain"), founder.get("primary_subdomain"))
        c_primary_pair = (company.get("primary_domain"), company.get("primary_subdomain"))
        if f_primary_pair == c_primary_pair and f_primary_pair[0] not in ("", "other", None):
            return 30, "perfect_match"

        f_pairs = self._pairs(founder)
        c_pairs = self._pairs(company)
        n_shared = len(f_pairs & c_pairs)
        f_primary = founder.get("primary_domain")
        c_primary = company.get("primary_domain")
        same_primary = f_primary == c_primary and f_primary not in ("", "other", None)

        # Any shared (domain, subdomain) tuple — whether on primary or secondary
        # on either side — counts as a subdomain match. Smooth: 24 floor, +2 per
        # extra shared pair, cap at 28.
        if n_shared >= 1:
            return min(28, 24 + 2 * (n_shared - 1)), "subdomain_match"

        # Same primary domain but no shared (domain, subdomain) tuple —
        # raised from 14 → 18 to reflect that same-primary alone is real signal.
        if same_primary:
            return 18, "domain_only"

        # Cross-domain shared subdomain STRING (different primaries, but same
        # subdomain word appears under both — e.g., founder healthcare/imaging
        # vs company ai-ml/imaging). Smooth: 10 base, +2 per extra, cap 14.
        f_subs = {s for _, s in f_pairs if s}
        c_subs = {s for _, s in c_pairs if s}
        cross = f_subs & c_subs
        if cross:
            return min(14, 10 + 2 * (len(cross) - 1)), "cross_domain_subdomain"

        if self._adjacent(f_primary, c_primary):
            return 6, "adjacent_domain"

        return 0, "no_overlap"

    def _pairs(self, tags: dict) -> set[tuple[str, str]]:
        pairs = set()
        primary = tags.get("primary_domain")
        sub = tags.get("primary_subdomain")
        if primary and primary != "other" and sub:
            pairs.add((primary, sub))
        for item in tags.get("secondary_subdomains") or []:
            d = item.get("domain")
            s = item.get("subdomain")
            if d and d != "other" and s:
                pairs.add((d, s))
        return pairs

    def _adjacent(self, d1: str | None, d2: str | None) -> bool:
        if not d1 or not d2 or "other" in (d1, d2):
            return False
        adjacency = taxonomy().get("adjacency") or {}
        return d2 in adjacency.get(d1, []) or d1 in adjacency.get(d2, [])

    def _keyword_jaccard(self, founder_keywords: list[str], company_keywords: list[str]) -> tuple[float, list[str]]:
        f_tokens = self._keyword_tokens(founder_keywords)
        c_tokens = self._keyword_tokens(company_keywords)
        union = f_tokens | c_tokens
        if not union:
            return 0.0, []
        shared = sorted(f_tokens & c_tokens)
        return len(shared) / len(union), shared

    def _keyword_tokens(self, keywords: list[str]) -> set[str]:
        tokens = set()
        for kw in keywords:
            for tok in TOKEN_RE.findall(str(kw).lower().replace("-", " ")):
                if len(tok) <= 1:
                    continue
                tokens.add(synonyms().get(tok, tok))
        return tokens

    def _apply_weak_company_fallback(
        self,
        compared: dict,
        founder_tags: dict,
        company_tags: dict,
        evidence_level: str,
        profile: dict,
        filing: dict,
    ) -> None:
        if evidence_level not in {"weak", "name_only"}:
            return
        if company_tags.get("classification_confidence") != "low":
            return
        if not self._has_clear_founder_domain(founder_tags):
            return
        if not self._is_current_operator(profile, filing):
            return

        floor = self._weak_company_floor(founder_tags, profile, filing)
        if compared["final_score"] >= floor:
            return
        compared["weak_company_original_score"] = compared["final_score"]
        compared["weak_company_original_match_type"] = compared["match_type"]
        compared["base_score"] = floor
        compared["adjustment"] = 0
        compared["final_score"] = floor
        compared["match_type"] = f"weak_company_founder_floor_{floor}"

    def _has_clear_founder_domain(self, founder_tags: dict) -> bool:
        return (
            founder_tags.get("primary_domain") not in ("", "other", None)
            and founder_tags.get("primary_subdomain") not in ("", None)
        )

    def _weak_company_floor(self, founder_tags: dict, profile: dict, filing: dict) -> int:
        floor = 4
        keywords = founder_tags.get("keywords") or []
        secondary = founder_tags.get("secondary_subdomains") or []
        if len(keywords) >= 3 or secondary:
            floor = 5
        if floor >= 5 and self._has_repeated_nonissuer_experience(profile, filing):
            floor = 6
        return min(6, floor)

    def _is_current_operator(self, profile: dict, filing: dict) -> bool:
        entity = filing.get("entity_name") or ""
        current_title = str(profile.get("current_title") or "")
        current_company = str(profile.get("current_company") or "")
        if self._operator_title_matches(current_title) and self._company_matches(current_company, entity):
            return True

        for exp in get_experience(profile)[:2]:
            title = get_title(exp)
            company = get_company_name(exp)
            if self._operator_title_matches(title) and self._company_matches(company, entity):
                return True
        return False

    def _operator_title_matches(self, title: str) -> bool:
        return bool(OPERATOR_TITLE_RE.search(title or ""))

    def _has_repeated_nonissuer_experience(self, profile: dict, filing: dict) -> bool:
        entity = filing.get("entity_name") or ""
        count = 0
        for exp in get_experience(profile):
            company = get_company_name(exp)
            title = get_title(exp)
            if not title or self._company_matches(company, entity):
                continue
            count += 1
            if count >= 2:
                return True
        return False

    def _company_matches(self, company_name: str, entity_name: str) -> bool:
        company = self._normalize_company_name(company_name)
        entity = self._normalize_company_name(entity_name)
        if not company or not entity:
            return False
        if company == entity:
            return True
        if len(company) >= 5 and len(entity) >= 5:
            return company in entity or entity in company
        return False

    def _normalize_company_name(self, name: str) -> str:
        text = re.sub(r"[^a-z0-9& ]+", " ", (name or "").lower())
        tokens = [t for t in text.split() if t and t not in LEGAL_SUFFIXES]
        return " ".join(tokens)

    def _empty_breakdown(self) -> dict:
        return {
            "base_score": 0,
            "adjustment": 0,
            "final_score": 0,
            "match_type": "no_company",
            "keyword_jaccard": 0,
            "shared_keywords": [],
        }
