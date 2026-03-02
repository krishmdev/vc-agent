"""Horsepower (0-30): did the founder climb fast, sustain altitude, and grow? Duration-weighted
title level (0-21), education (0-6) and a recent-trajectory bonus (0-3). Ported from
sierra-demo's horsepower_scorer."""

from __future__ import annotations

import re

from .profile import (
    duration_months,
    get_company_name,
    get_degree_name,
    get_education,
    get_end_date,
    get_experience,
    get_major_text,
    get_school_name,
    get_start_date,
    get_title,
    is_founder_title,
)
from .titles import classify_title

# Founder-dense schools (sierra-demo's list).
TOP_SCHOOLS = {
    "stanford university", "stanford",
    "massachusetts institute of technology", "mit",
    "carnegie mellon university", "cmu",
    "university of california, berkeley", "uc berkeley", "berkeley",
    "california institute of technology", "caltech",
    "harvard university", "harvard",
    "princeton university", "princeton",
    "yale university", "yale",
    "cornell university", "cornell",
    "columbia university", "columbia",
    "university of pennsylvania", "upenn", "penn",
    "georgia institute of technology", "georgia tech",
    "university of michigan",
    "university of illinois",
    "university of washington",
    "eth zurich",
    "university of oxford", "oxford",
    "university of cambridge", "cambridge",
    "indian institute of technology", "iit",
    "tsinghua university",
    "peking university",
    "national university of singapore",
    "university of waterloo", "waterloo",
    "university of toronto",
    "duke university", "duke",
    "northwestern university",
    "rice university",
    "brown university",
    "dartmouth college",
    "university of texas at austin",
    "university of wisconsin-madison",
    "purdue university",
    "university of maryland",
}


STEM_RE = re.compile(
    r"\b(computer|science|engineering|biology|bioengineering|biotech|medicine|medical|"
    r"physics|chemistry|math|mathematics|statistics|machine learning|artificial intelligence|"
    r"robotics|genomics|neuroscience|materials|aerospace|electrical|mechanical)\b",
    re.I,
)
POSTDOC_TITLE_RE = re.compile(r"\b(postdoc|postdoctoral|research fellow)\b", re.I)
RESEARCH_ORG_RE = re.compile(r"\b(university|institute|national lab|laboratory|lab)\b", re.I)
ELITE_TECH_ROLE_RE = re.compile(
    r"\b(machine learning|ml engineer|ai engineer|research engineer|research scientist|"
    r"applied scientist|quant|quantitative|compiler|robotics|security engineer|"
    r"infrastructure engineer|distributed systems)\b",
    re.I,
)
STRONG_TECH_ROLE_RE = re.compile(
    r"\b(software engineer|backend engineer|front[\s-]?end engineer|full[\s-]?stack engineer|"
    r"data engineer|platform engineer|hardware engineer|systems engineer|developer|"
    r"architect|technical lead)\b",
    re.I,
)
HYBRID_TECH_ROLE_RE = re.compile(
    r"\b(forward deployed engineer|fde|solutions engineer|solution engineer|sales engineer|"
    r"implementation engineer|customer engineer)\b",
    re.I,
)


def _norm_school(value: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", value.lower()).strip()


# Common alternate names for schools on the list. sierra-demo matched by substring and a fuzzy
# ratio, which also credited Smith College ("mit"), Penn State, Northeastern ("northwestern"),
# Harvard Extension and a bare "University". Here a school must match a list entry or one of these
# aliases exactly after normalization.
SCHOOL_ALIASES = {
    "stanford graduate school of business": "stanford university",
    "harvard business school": "harvard university",
    "harvard college": "harvard university",
    "mit sloan school of management": "massachusetts institute of technology",
    "massachusetts institute of technology mit": "massachusetts institute of technology",
    "the wharton school": "university of pennsylvania",
    "wharton school of the university of pennsylvania": "university of pennsylvania",
    "university of michigan ann arbor": "university of michigan",
    "university of illinois urbana champaign": "university of illinois",
    "university of illinois at urbana champaign": "university of illinois",
    "university of washington seattle": "university of washington",
    "uc berkeley haas": "university of california berkeley",
    "iit bombay": "indian institute of technology",
    "iit delhi": "indian institute of technology",
    "iit madras": "indian institute of technology",
    "iit kanpur": "indian institute of technology",
    "iit kharagpur": "indian institute of technology",
    "iit roorkee": "indian institute of technology",
    "iit guwahati": "indian institute of technology",
    "carnegie mellon": "carnegie mellon university",
    "stanford gsb": "stanford university",
    "stanford school of engineering": "stanford university",
    "mit sloan": "massachusetts institute of technology",
    "harvard university graduate school of arts and sciences": "harvard university",
    "university of california at berkeley": "university of california berkeley",
    "uc berkeley college of engineering": "university of california berkeley",
    "georgia institute of technology atlanta": "georgia institute of technology",
    "eth z rich": "eth zurich",
    "nus": "national university of singapore",
    "university of illinois at urbana champaign uiuc": "university of illinois",
    "uiuc": "university of illinois",
    "ut austin": "university of texas at austin",
    "uw madison": "university of wisconsin madison",
}
_FOUNDER_SCHOOLS = {re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s.lower())).strip() for s in TOP_SCHOOLS}


def _is_founder_school(school: str) -> bool:
    normalized = re.sub(r"\s+", " ", _norm_school(school))
    if not normalized:
        return False
    return normalized in _FOUNDER_SCHOOLS or normalized in SCHOOL_ALIASES


def _degree_kind(degree: str) -> str:
    d = (degree or "").lower()
    if any(k in d for k in ("phd", "ph.d", "doctorate", "doctor of philosophy", "doctoral")):
        return "phd"
    if any(k in d for k in ("master", "masters", "mba", "m.s", "m.eng", "m.a")) or re.fullmatch(r"m[as]|ms|ma", d.strip()):
        return "masters"
    if any(k in d for k in ("bachelor", "ba ", "bs ", "b.s", "b.a", "undergraduate")):
        return "bachelors"
    return "unknown"


class HorsepowerScorer:
    def score(self, profile: dict, company_tags: dict | None = None, as_of: str | None = None) -> dict:
        """`as_of` (YYYY-MM) closes open-ended roles for duration weighting. sierra-demo dropped a
        current role with no end date from the weighting; here it counts up to `as_of`."""
        experience = get_experience(profile)
        education = get_education(profile)
        classified = []
        dated = []

        for exp in experience:
            title = get_title(exp)
            if is_founder_title(title):
                continue
            if POSTDOC_TITLE_RE.search(title) and RESEARCH_ORG_RE.search(get_company_name(exp)):
                base_level = 4
            else:
                base_level = classify_title(title, include_founder=False)
            if base_level is None:
                continue
            modifier = self._role_modifier(title)
            level = max(1.0, min(6.0, base_level + modifier))
            item = {
                "title": title,
                "company": get_company_name(exp),
                "level": level,
                "base_level": base_level,
                "role_modifier": modifier,
                "start_date": get_start_date(exp),
                "end_date": get_end_date(exp) or (as_of if get_start_date(exp) else None),
            }
            classified.append(item)
            months = duration_months(item["start_date"], item["end_date"])
            if months:
                dated.append({**item, "duration_months": months})

        date_handling = "none"
        weighted_level = 0.0
        if len(dated) >= 2:
            total_months = sum(d["duration_months"] for d in dated)
            weighted_level = sum(d["level"] * d["duration_months"] for d in dated) / total_months
            date_handling = "duration_weighted"
        elif classified:
            weighted_level = sum(d["level"] for d in classified) / len(classified)
            date_handling = "unweighted_average_missing_dates"
        else:
            synthetic_level = self._synthetic_research_level(experience, education, company_tags)
            if synthetic_level is not None:
                weighted_level = synthetic_level
                classified.append({
                    "title": "Synthetic PhD/post-doc research role",
                    "company": None,
                    "level": synthetic_level,
                })
                date_handling = "synthetic_research_role"

        weighted_level_score = self._weighted_level_points(weighted_level)
        education_bonus, education_detail = self._education_bonus(education, experience)
        trajectory_bonus = self._trajectory_bonus(dated)
        # Components sum to a hard 30 max (21 + 6 + 3), so no clamp is needed.
        total = weighted_level_score + education_bonus + trajectory_bonus

        return {
            "hp_score": round(total, 3),
            "hp_weighted_level": round(weighted_level, 3),
            "hp_weighted_level_score": weighted_level_score,
            "hp_education_bonus": education_bonus,
            "hp_trajectory_bonus": trajectory_bonus,
            "hp_date_handling": date_handling,
            "breakdown": {
                "classified_roles": classified,
                "dated_roles": dated,
                "education": education_detail,
            },
        }

    def _trajectory_bonus(self, dated: list[dict]) -> int:
        # Reward upward title progression across the last 3 dated roles.
        # +3 for a 2+ level climb, +1 for a 1 level climb. Plateaus get 0.
        if len(dated) < 3:
            return 0
        by_start = sorted(dated, key=lambda d: d.get("start_date") or "")
        recent = by_start[-3:]
        levels = [d["level"] for d in recent]
        if not (levels[0] <= levels[1] <= levels[2]):
            return 0
        climb = levels[2] - levels[0]
        if climb >= 2:
            return 3
        if climb >= 1:
            return 1
        return 0

    def _role_modifier(self, title: str) -> float:
        # Positive-only modifier. Non-technical or ambiguous roles add 0,
        # because weak evidence should not become a punitive HP deduction.
        if ELITE_TECH_ROLE_RE.search(title):
            return 0.75
        if STRONG_TECH_ROLE_RE.search(title):
            return 0.5
        if HYBRID_TECH_ROLE_RE.search(title):
            return 0.25
        return 0.0

    def _weighted_level_points(self, weighted_level: float) -> int:
        # Piecewise-linear smoothing. Preserves the original bucket anchors
        # (1.5 → 5, 2.5 → 11, 3.5 → 16, 4.5 → 21) but interpolates between
        # them so a founder at 4.49 doesn't drop 5 points vs one at 4.50.
        wl = weighted_level
        if wl >= 4.5:
            return 21
        if wl >= 3.5:
            return round(16 + (wl - 3.5) * 5)   # 16..21
        if wl >= 2.5:
            return round(11 + (wl - 2.5) * 5)   # 11..16
        if wl >= 1.5:
            return round(5 + (wl - 1.5) * 6)    # 5..11
        if wl >= 0.5:
            return round((wl - 0.5) * 5)         # 0..5
        return 0

    def _education_bonus(self, education: list[dict], experience: list[dict]) -> tuple[int, dict]:
        best = 0
        best_detail = {"degree": None, "school": None, "founder_school": False, "source": None}

        for edu in education:
            school = get_school_name(edu)
            degree = get_degree_name(edu)
            kind = _degree_kind(degree)
            founder_school = _is_founder_school(school)
            points = 0
            if kind == "phd":
                points = 6 if founder_school else 5
            elif kind == "masters":
                points = 4 if founder_school else 2
            elif kind == "bachelors":
                points = 1 if founder_school else 0
            if points > best:
                best = points
                best_detail = {"degree": degree, "school": school, "founder_school": founder_school, "source": "education"}

        if self._has_postdoc(experience):
            # Treat post-doc as PhD-equivalent, but preserve a founder-school PhD if present.
            if best < 5:
                best = 5
                best_detail = {"degree": "post-doc/research fellow", "school": None, "founder_school": False, "source": "experience"}

        return best, best_detail

    def _has_postdoc(self, experience: list[dict]) -> bool:
        for exp in experience:
            if POSTDOC_TITLE_RE.search(get_title(exp)) and RESEARCH_ORG_RE.search(get_company_name(exp)):
                return True
        return False

    def _synthetic_research_level(
        self,
        experience: list[dict],
        education: list[dict],
        company_tags: dict | None,
    ) -> float | None:
        # PDL often under-represents PhD research as "education" only, even
        # though 4-7 years of applied research is career signal. We synthesize
        # a role only when there are no measurable non-founder roles, and only
        # for research-heavy domains/fields.
        research_heavy_domains = {
            "ai-ml",
            "healthcare",
            "robotics",
            "quantum",
            "hardware",
            "space-aerospace",
            "climate-energy",
        }
        domain = (company_tags or {}).get("primary_domain", "")
        research_heavy_company = domain in research_heavy_domains

        if self._has_postdoc(experience):
            return 4.0
        for edu in education:
            if _degree_kind(get_degree_name(edu)) == "phd":
                field = f"{get_degree_name(edu)} {get_major_text(edu)}"
                stem_field = bool(STEM_RE.search(field))
                if not stem_field and not research_heavy_company:
                    continue
                school = get_school_name(edu)
                if _is_founder_school(school) and research_heavy_company:
                    return 4.0
                if stem_field and research_heavy_company:
                    return 3.5
                if stem_field:
                    return 3.0
        return None
