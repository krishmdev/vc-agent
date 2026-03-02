"""Curated high-outcome company registry and name matcher (ported from sierra-demo).

The list (data/high_outcome_companies.json, 465 companies) is hand-built: a company is on it
because it's a recognized founder factory, not because it's large. Matching is exact on the
normalized name or an alias, else a rapidfuzz ratio >= 85 on names that share a non-generic
token. Short names (3 characters or fewer) only match exactly.

Two deviations from sierra-demo, both in code so the data file stays byte-identical:
- Stock-ticker aliases (a single token of 4 characters or fewer that isn't the company's own
  name: "team" for Atlassian, "frog" for JFrog, "open", "dash", "z") only match when the input
  is written in capitals, like a ticker. Otherwise "Team Rubicon" or "Open Road" matched.
- An alias can't take over another company's canonical name ("segment" is Segment, not an alias
  of Twilio Segment). Otherwise the index is last-write-wins, as in sierra-demo.

The file lists 13 companies more than once; 4 of them with conflicting tiers (elastic, plaid,
marqeta, brex). The later entry wins for any key both entries share, as in sierra-demo, so
scores stay comparable; an alias only the earlier entry lists ("elasticsearch") still points to
the earlier entry.
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
TICKER_ALIAS_MAX_LEN = 4


def normalize_company_name(name: str) -> str:
    text = re.sub(r"[^a-z0-9& ]+", " ", (name or "").lower())
    tokens = [t for t in text.split() if t and t not in LEGAL_SUFFIXES]
    return " ".join(tokens)


def is_ticker_alias(alias: str, company_name: str) -> bool:
    return " " not in alias and len(alias) <= TICKER_ALIAS_MAX_LEN and alias != normalize_company_name(company_name)


class CompanyRegistry:
    def __init__(self, path: Path | str = HIGH_OUTCOME_COMPANIES_PATH):
        self.path = Path(path)
        self.companies = self._load()
        self.alias_index: dict[str, dict] = {}
        self.ticker_index: dict[str, dict] = {}
        self.aliases: list[tuple[str, dict]] = []
        canonical = {normalize_company_name(c.get("name", "")) for c in self.companies} - {""}
        # Same order as sierra-demo (each company's name, then its aliases) so fuzzy ties resolve
        # the same way. Later entries overwrite earlier ones, as in sierra-demo, except that an
        # alias never overwrites a canonical name and tickers live in their own index.
        for company in self.companies:
            name = normalize_company_name(company.get("name", ""))
            if name:
                self.alias_index[name] = company
                self.aliases.append((name, company))
            for alias in company.get("aliases") or []:
                normalized = normalize_company_name(alias)
                if not normalized or normalized == name:
                    continue
                if is_ticker_alias(normalized, company.get("name", "")):
                    self.ticker_index[normalized] = company
                    continue
                if normalized not in canonical:
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
        stripped = (name or "").strip()
        if stripped.isupper() and normalized in self.ticker_index:
            return self.ticker_index[normalized], 100.0, "ticker"

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
