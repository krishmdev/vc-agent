"""Curated high-outcome company registry and name matcher (ported from sierra-demo).

The list (data/high_outcome_companies.json, 465 companies) is hand-built: a company is on it
because it's a recognized founder factory, not because it's large. Matching is exact on the
normalized name or an alias, else a rapidfuzz ratio >= 85 on names that share a non-generic
token. Short names (3 characters or fewer) only match exactly.
"""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path

from rapidfuzz import fuzz

DATA_DIR = Path(__file__).resolve().parent / "data"
HIGH_OUTCOME_COMPANIES_PATH = DATA_DIR / "high_outcome_companies.json"

BUCKET_TO_TIER = {
    "$50B+": 0,
    "$10B-$50B": 1,
    "$1B-$10B": 2,
    "$200M-$1B": 3,
}
LEGAL_SUFFIXES = {
    "inc", "incorporated", "corp", "corporation", "co", "company", "llc",
    "ltd", "limited", "plc", "gmbh", "sa", "ag", "holdings", "holding",
}
GENERIC_MATCH_WORDS = {"technologies", "technology", "systems", "holdings", "labs", "group"}
SHORT_ALIAS_MAX_LEN = 3
TECHNICAL_ROLE_WORDS = {
    "engineer", "engineering", "scientist", "research", "researcher", "developer",
    "product", "platform", "infrastructure", "infra", "security", "technical",
    "technology", "data", "analytics", "semiconductor", "hardware", "software",
    "architect", "cloud", "network", "telecom", "medical", "device", "aerospace",
    "space", "materials", "risk",
}


def normalize_company_name(name: str) -> str:
    text = re.sub(r"[^a-z0-9& ]+", " ", (name or "").lower())
    tokens = [t for t in text.split() if t and t not in LEGAL_SUFFIXES]
    return " ".join(tokens)


def _tokens(name: str) -> set[str]:
    return set(normalize_company_name(name).split())


class CompanyRegistry:
    def __init__(self, path: Path | str = HIGH_OUTCOME_COMPANIES_PATH):
        self.path = Path(path)
        self.companies = self._load()
        self.alias_index: dict[str, dict] = {}
        self.aliases: list[tuple[str, dict]] = []
        for company in self.companies:
            names = [company.get("name", "")] + list(company.get("aliases") or [])
            for name in names:
                normalized = normalize_company_name(name)
                if not normalized:
                    continue
                self.alias_index[normalized] = company
                self.aliases.append((normalized, company))

    def _load(self) -> list[dict]:
        with self.path.open() as f:
            data = json.load(f)
        return list(data.get("companies") or [])

    def match(self, name: str) -> tuple[dict | None, float, str]:
        normalized = normalize_company_name(name)
        if not normalized:
            return None, 0.0, "none"

        exact = self.alias_index.get(normalized)
        if exact:
            return exact, 100.0, "exact"

        name_tokens = set(normalized.split())
        if len(normalized) <= SHORT_ALIAS_MAX_LEN:
            return None, 0.0, "short_no_exact"

        best_company = None
        best_score = 0.0
        best_alias = ""
        for alias, company in self.aliases:
            if len(alias) <= SHORT_ALIAS_MAX_LEN:
                continue
            alias_tokens = set(alias.split())
            if not alias_tokens:
                continue
            overlap = name_tokens & alias_tokens
            if not overlap or overlap <= GENERIC_MATCH_WORDS:
                continue
            if len(alias_tokens) == 1 and next(iter(alias_tokens)) in GENERIC_MATCH_WORDS:
                continue
            score = fuzz.ratio(normalized, alias)
            if score >= 85 and score > best_score:
                best_score = float(score)
                best_company = company
                best_alias = alias

        return best_company, best_score, f"fuzzy:{best_alias}" if best_company else "none"

    @staticmethod
    def scoring_tier(company: dict) -> int | None:
        override = company.get("scoring_tier_override")
        if override is not None:
            try:
                return int(override)
            except (TypeError, ValueError):
                pass
        bucket = company.get("peak_valuation_bucket")
        if bucket in BUCKET_TO_TIER:
            return BUCKET_TO_TIER[bucket]
        tier = company.get("tier")
        try:
            raw = int(tier)
        except (TypeError, ValueError):
            return None
        if raw in (1, 2, 3):
            return raw
        return None



@cache
def default_registry() -> CompanyRegistry:
    return CompanyRegistry()
