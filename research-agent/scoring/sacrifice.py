"""Sacrifice (0-5): what seniority or stability did the founder give up to start this company?
Ported from sierra-demo's sacrifice_scorer."""

from __future__ import annotations

from .profile import (
    get_company_name,
    get_end_date,
    get_experience,
    get_start_date,
    get_title,
    is_founder_title,
    parse_year,
)
from .registry import CompanyRegistry, default_registry
from .titles import classify_title


# Points for leaving a recognized high-outcome company to found.
# Mirrors CompanyRegistry scoring tiers (0=mega-cap … 3=growth-stage).
TIER_POINTS = {0: 5, 1: 4, 2: 3, 3: 2}

# Fallback when the prior company isn't in the registry. Senior leadership at
# an unknown company still represents real seniority sacrificed to found.
# Level 6 = C-suite, Level 5 = VP / Head of.
UNKNOWN_LEVEL_POINTS = {6: 2, 5: 1}


class SacrificeScorer:
    def __init__(self, registry: CompanyRegistry | None = None):
        self._registry = registry

    @property
    def registry(self) -> CompanyRegistry:
        if self._registry is None:
            self._registry = default_registry()
        return self._registry

    def score(self, profile: dict, filing: dict | None = None) -> dict:
        experience = get_experience(profile)
        founding_idx = self._founding_role_index(experience, profile, filing)
        prior = None

        if founding_idx is not None:
            prior = self._prior_role_by_dates(experience, founding_idx) or self._prior_role_by_order(experience, founding_idx)

        prior_company_name = get_company_name(prior) if prior else ""
        matched, match_score, match_method = self.registry.match(prior_company_name) if prior_company_name else (None, 0.0, "none")
        tier = self.registry.scoring_tier(matched) if matched else None
        prior_title = get_title(prior) if prior else ""
        prior_level = classify_title(prior_title, include_founder=False) if prior_title else None

        if matched and tier is not None:
            points = TIER_POINTS.get(tier, 0)
            score_source = f"registry_tier_{tier}"
        else:
            points = UNKNOWN_LEVEL_POINTS.get(prior_level or -1, 0)
            score_source = f"unknown_level_{prior_level}" if points else "no_signal"

        return {
            "sacrifice_score": points,
            "breakdown": {
                "prior_role": {
                    "title": prior_title or None,
                    "company": prior_company_name or None,
                    "level": prior_level,
                    "matched_company": matched.get("name") if matched else None,
                    "matched_tier": tier,
                    "match_score": round(match_score, 1),
                    "match_method": match_method,
                    "score_source": score_source,
                },
                "founding_role_index": founding_idx,
            },
        }

    def _founding_role_index(self, experience: list[dict], profile: dict, filing: dict | None) -> int | None:
        entity = (filing or {}).get("entity_name") or profile.get("current_company") or ""
        entity = entity.lower()
        for idx, exp in enumerate(experience):
            title = get_title(exp)
            company = get_company_name(exp).lower()
            if is_founder_title(title):
                return idx
            if idx == 0 and entity and (entity in company or company in entity):
                return idx
        return 0 if experience else None

    def _prior_role_by_order(self, experience: list[dict], founding_idx: int) -> dict | None:
        if founding_idx + 1 < len(experience):
            return experience[founding_idx + 1]
        return None

    def _prior_role_by_dates(self, experience: list[dict], founding_idx: int) -> dict | None:
        founding = experience[founding_idx]
        founding_start = parse_year(get_start_date(founding))
        if not founding_start:
            return None
        candidates = []
        for idx, exp in enumerate(experience):
            if idx == founding_idx:
                continue
            end_year = parse_year(get_end_date(exp))
            start_year = parse_year(get_start_date(exp))
            if end_year and end_year <= founding_start:
                candidates.append((end_year, idx, exp))
            elif start_year and start_year < founding_start:
                candidates.append((start_year, idx, exp))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[0], -x[1]), reverse=True)
        return candidates[0][2]
