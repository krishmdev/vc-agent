"""Seen Greatness (0-35): did the founder build, lead, or work inside an exceptional company,
and how senior and how early were they? Ported from sierra-demo's seen_greatness_scorer."""

from __future__ import annotations

import re
from typing import Any

from .profile import (
    duration_months,
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


BASE_POINTS = {0: 11.5, 1: 10.0, 2: 8.5, 3: 7.0}
SMALL_CO_BUILDER_BONUS = 4.0

# Smooth duration-based bonus for prior founder roles at unknown companies:
# bonus = min(PRIOR_FOUNDER_CAP, PRIOR_FOUNDER_BASE + PRIOR_FOUNDER_SLOPE * years)
# Plus a large flat +REGISTRY_PREMIUM if the prior company is in our registry.
# Avoids the 2.9-yr→3.0-yr cliff that earlier brief/sustained tiers created.
PRIOR_FOUNDER_BASE = 5.0
PRIOR_FOUNDER_SLOPE = 1.2
PRIOR_FOUNDER_CAP = 8.0
PRIOR_FOUNDER_REGISTRY_PREMIUM = 6.0
TECHNICAL_ROLE_WORDS = {
    "engineer", "engineering", "scientist", "research", "researcher", "developer",
    "product", "platform", "infrastructure", "infra", "security", "technical",
    "technology", "data", "analytics", "semiconductor", "hardware", "software",
    "architect", "cloud", "network", "telecom", "medical", "device", "aerospace",
    "space", "materials", "risk",
}


class SeenGreatnessScorer:
    def __init__(self, registry: CompanyRegistry | None = None):
        self.registry = registry or default_registry()

    def matched_categories(self, profile: dict) -> list[dict]:
        categories = []
        for exp in get_experience(profile):
            matched, score, method = self.registry.match(get_company_name(exp))
            if matched:
                categories.append({
                    "company": matched.get("name"),
                    "category": matched.get("category"),
                    "match_score": score,
                    "match_method": method,
                })
        return categories

    def score(self, profile: dict) -> dict:
        experience = get_experience(profile)
        considered = []
        # Track best-scoring item per unique company name. Multiple roles at
        # the same company (e.g., 4 different VP titles at Microsoft) collapse
        # to the single best, and the final SG company subtotal uses the single
        # best employer across the whole career. The signal is "have you seen
        # greatness," not "how many resume logos can we count."
        best_per_company: dict[str, dict] = {}

        for exp in experience:
            company_name = get_company_name(exp)
            matched, match_score, method = self.registry.match(company_name)
            if not matched:
                continue

            title = get_title(exp)
            if not self._role_qualifies(title, matched):
                considered.append({"company": matched.get("name"), "title": title, "skipped": "role_qualifier"})
                continue

            scoring_tier = self.registry.scoring_tier(matched)
            if scoring_tier not in BASE_POINTS:
                continue
            level = classify_title(title, include_founder=False)
            seniority = self._seniority_multiplier(level, match_score)
            if seniority == 0:
                considered.append({"company": matched.get("name"), "title": title, "skipped": "unknown_title"})
                continue
            earliness = self._earliness_multiplier(get_start_date(exp), matched.get("inflection_year"))
            base = BASE_POINTS[scoring_tier]
            points = base * seniority * earliness
            item = {
                "company": matched.get("name"),
                "title": title,
                "points": round(points, 3),
                "tier": scoring_tier,
                "raw_tier": matched.get("tier"),
                "base_points": base,
                "seniority_multiplier": seniority,
                "earliness_multiplier": earliness,
                "inflection_year": matched.get("inflection_year"),
                "join_year": parse_year(get_start_date(exp)),
                "match_score": match_score,
                "match_method": method,
            }
            considered.append(item)
            key = matched.get("name") or company_name
            if points > best_per_company.get(key, {}).get("points", 0):
                best_per_company[key] = {**item, "matched_company_tier": matched.get("tier")}

        # Sum best-per-unique-company across the career. Multiple roles at the
        # same company collapse to one (best Microsoft role only counts once),
        # but distinct registry companies (Microsoft + Amazon + NASA) each
        # contribute. Rewards career breadth without rewarding role-count
        # inflation.
        company_score = sum(c["points"] for c in best_per_company.values())
        best = max(best_per_company.values(), key=lambda c: c["points"], default={
            "points": 0.0, "company": None, "tier": None, "raw_tier": None, "title": None,
            "base_points": 0.0, "seniority_multiplier": 0.0, "earliness_multiplier": 0.0,
            "match_method": None,
        })

        founder_bonus, founder_bonus_kind = self._prior_founder_bonus(experience)
        builder_bonus = SMALL_CO_BUILDER_BONUS if self._has_small_co_builder_role(experience) else 0.0
        total = min(35.0, company_score + founder_bonus + builder_bonus)

        return {
            "seen_greatness_score": round(total, 3),
            "matched_company": best.get("company"),
            "matched_company_tier": best.get("matched_company_tier") or best.get("raw_tier"),
            "matched_company_scoring_tier": best.get("tier"),
            "breakdown": {
                "best_company": best,
                "company_score_total": round(company_score, 3),
                "company_scoring_mode": "sum_best_per_unique_company",
                "matched_companies": list(best_per_company.keys()),
                "prior_founder_bonus": founder_bonus,
                "prior_founder_kind": founder_bonus_kind,
                "small_co_builder_bonus": builder_bonus,
                "considered": considered,
            },
        }

    def _role_qualifies(self, title: str, company: dict) -> bool:
        qualifier = (company.get("role_qualifier") or "").strip().lower()
        if not qualifier:
            return True
        title_tokens = set(re.findall(r"[a-z0-9]+", title.lower()))
        return bool(title_tokens & TECHNICAL_ROLE_WORDS)

    def _seniority_multiplier(self, level: int | None, match_score: float) -> float:
        if level is None:
            return 0.6 if match_score >= 100 else 0.0
        if level >= 4:
            return 1.5
        if level == 3:
            return 1.0
        if level in (1, 2):
            return 0.6
        return 0.0

    def _earliness_multiplier(self, start_value: Any, inflection_year: Any) -> float:
        # Graded timing signal:
        # - Pre-inflection roles get the strongest credit.
        # - Inflection-year roles get a small bump.
        # - Post-inflection roles stay at 1.0×. Late exposure is still captured
        #   by the company tier base; it is not "earliness."
        join_year = parse_year(start_value)
        try:
            inflection = int(inflection_year)
        except (TypeError, ValueError):
            return 1.0
        if not join_year:
            return 1.0
        years_before = inflection - join_year
        if years_before >= 1:
            return min(1.3, 1.0 + 0.09 * years_before)
        if years_before == 0:
            return 1.08
        return 1.0
 
    def _prior_founder_bonus(self, experience: list[dict]) -> tuple[float, str]:
        # Smooth duration-based bonus + flat registry premium. Skip experience[0]
        # (current Form D role) and consider all earlier founder roles, returning
        # the best-scoring one.
        prior = experience[1:] if experience else []
        best_pts = 0.0
        best_kind = "none"
        for exp in prior:
            if not is_founder_title(get_title(exp)):
                continue
            company_name = get_company_name(exp)
            matched, _, _ = self.registry.match(company_name) if company_name else (None, 0.0, "none")
            months = duration_months(get_start_date(exp), get_end_date(exp)) or 0
            years = months / 12.0
            duration_pts = min(PRIOR_FOUNDER_CAP, PRIOR_FOUNDER_BASE + PRIOR_FOUNDER_SLOPE * years)
            registry_pts = PRIOR_FOUNDER_REGISTRY_PREMIUM if matched else 0.0
            pts = duration_pts + registry_pts
            if pts > best_pts:
                best_pts = pts
                best_kind = "validated" if matched else ("sustained" if years >= 3 else "brief")
        return best_pts, best_kind

    def _has_small_co_builder_role(self, experience: list[dict]) -> bool:
        # Builder = senior leadership (level ≥ 5) at a company NOT in our registry.
        # Captures "VP at small startup" — a startup-immersion proxy for companies
        # we don't have registry data on. Skips the current Form D founding role.
        prior = experience[1:] if experience else []
        for exp in prior:
            title = get_title(exp)
            if is_founder_title(title):
                continue
            company_name = get_company_name(exp)
            if not company_name:
                continue
            matched, _, _ = self.registry.match(company_name)
            if matched:
                # Already credited via registry tier scoring.
                continue
            level = classify_title(title, include_founder=False)
            lower = title.lower()
            explicit = any(
                phrase in lower
                for phrase in (
                    "vp engineering", "vp of engineering",
                    "vp product", "vp of product",
                    "head of engineering", "head of product",
                )
            )
            if (level is not None and level >= 5) or explicit:
                return True
        return False
