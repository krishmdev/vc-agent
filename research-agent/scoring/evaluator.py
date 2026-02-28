"""Founder scorecard: sierra-demo's composite plus evidence and advice for the founder.

composite = Seen Greatness (35) + Horsepower (30) + Domain Fit (30) + Sacrifice (5), a raw
0-100 sum. Bands: >= 60 strong, 45-59 secondary, < 45 filter (sierra-demo's starting points).
Timing (0-15) is reported alongside, not added in, same as sierra-demo.

Every evidence line is built from a scorer's breakdown, so each number on the scorecard can be
traced back to a role, a registry entry, or a tag. The advice is rule-based text keyed to those
same numbers; no model writes it.
"""

from __future__ import annotations

from datetime import date, datetime

from .classifier import DomainClassifier
from .domain_fit import DomainFitScorer, company_evidence_level
from .horsepower import HorsepowerScorer
from .profile import get_experience, get_title
from .sacrifice import SacrificeScorer
from .seen_greatness import SeenGreatnessScorer
from .timing import TimingScorer

ENGINE = "sierra-demo founder scoring, ported"
STRONG, SECONDARY = 60.0, 45.0

MAXIMA = {"seen_greatness": 35, "horsepower": 30, "domain_fit": 30, "sacrifice": 5, "timing": 15}
LABELS = {
    "seen_greatness": "Seen greatness",
    "horsepower": "Horsepower",
    "domain_fit": "Domain fit",
    "sacrifice": "Sacrifice",
    "timing": "Timing",
}


def verdict(composite: float) -> dict:
    if composite >= STRONG:
        return {"band": "strong", "label": "Strong: surface for partner review"}
    if composite >= SECONDARY:
        return {"band": "secondary", "label": "Secondary list"}
    return {"band": "filter", "label": "Below the bar for now"}


def _fmt(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".")


def _tag(tags: dict) -> str:
    d = tags.get("primary_domain") or "other"
    s = tags.get("primary_subdomain")
    return f"{d}/{s}" if s else d


def seen_greatness_evidence(sg: dict) -> list[dict]:
    b = sg["breakdown"]
    best: dict[str, dict] = {}
    for item in b["considered"]:
        if "points" in item and item["company"] in b["matched_companies"]:
            if item["points"] > best.get(item["company"], {}).get("points", -1):
                best[item["company"]] = item
    out = []
    for item in sorted(best.values(), key=lambda i: -i["points"]):
        joined = f", joined {item['join_year']}" if item.get("join_year") else ""
        inflection = f", inflection {item['inflection_year']}" if item.get("inflection_year") else ""
        out.append({
            "text": (
                f"{item['company'].title()} (tier {item['tier']}{inflection}): {item['title']}{joined}. "
                f"{_fmt(item['base_points'])} base x {_fmt(item['seniority_multiplier'])} seniority x "
                f"{_fmt(item['earliness_multiplier'])} earliness = {_fmt(item['points'])}"
            ),
            "source": "registry",
            "points": item["points"],
        })
    for item in b["considered"]:
        if item.get("skipped"):
            reason = "not a technical role at a technical company" if item["skipped"] == "role_qualifier" else "title not recognized"
            out.append({"text": f"{item['company'].title()}: {item['title']} not counted ({reason})", "source": "registry", "points": 0})
    if b["prior_founder_bonus"]:
        out.append({"text": f"Prior founder role ({b['prior_founder_kind']}): +{_fmt(b['prior_founder_bonus'])}", "source": "profile", "points": b["prior_founder_bonus"]})
    if b["small_co_builder_bonus"]:
        out.append({"text": f"VP-level or higher role at a company outside the registry: +{_fmt(b['small_co_builder_bonus'])}", "source": "profile", "points": b["small_co_builder_bonus"]})
    if not out:
        out.append({"text": "No employer matched the 465-company high-outcome registry", "source": "registry", "points": 0})
    if b["company_score_total"] + b["prior_founder_bonus"] + b["small_co_builder_bonus"] > MAXIMA["seen_greatness"]:
        out.append({"text": "Capped at 35", "source": "rule", "points": 0})
    return out


def horsepower_evidence(hp: dict) -> list[dict]:
    b = hp["breakdown"]
    out = []
    how = {
        "duration_weighted": "duration-weighted across dated roles",
        "unweighted_average_missing_dates": "plain average (dates missing)",
        "synthetic_research_role": "no non-founder roles; PhD research counted as a role",
        "none": "no classifiable roles",
    }[hp["hp_date_handling"]]
    out.append({
        "text": f"Weighted title level {_fmt(hp['hp_weighted_level'])} of 6 ({how}) -> {hp['hp_weighted_level_score']}/21",
        "source": "profile",
        "points": hp["hp_weighted_level_score"],
    })
    for role in b["classified_roles"]:
        mod = f", +{_fmt(role['role_modifier'])} technical role" if role.get("role_modifier") else ""
        company = f" at {role['company']}" if role.get("company") else ""
        out.append({"text": f"{role['title']}{company}: level {_fmt(role['level'])}{mod}", "source": "profile", "points": None})
    edu = b["education"]
    if hp["hp_education_bonus"]:
        where = f" at {edu['school']}" if edu.get("school") else ""
        tag = " (founder-dense school)" if edu.get("founder_school") else ""
        out.append({"text": f"{edu['degree']}{where}{tag}: +{hp['hp_education_bonus']}", "source": "profile", "points": hp["hp_education_bonus"]})
    if hp["hp_trajectory_bonus"]:
        out.append({"text": f"Title climbed across the last three roles: +{hp['hp_trajectory_bonus']}", "source": "profile", "points": hp["hp_trajectory_bonus"]})
    return out


def domain_fit_evidence(df: dict) -> list[dict]:
    b = df["breakdown"]
    if b.get("match_type") == "no_company":
        return [{"text": "No company description, so domain fit wasn't scored", "source": "rule", "points": 0}]
    f, c = b["founder_tags"], b["company_tags"]
    out = [
        {"text": f"Founder background: {_tag(f)} ({f.get('reason') or 'no reason'})", "source": "classifier", "points": None},
        {"text": f"Company: {_tag(c)} ({c.get('reason') or 'no reason'}; {b['company_evidence_level']} evidence)", "source": "classifier", "points": None},
    ]
    match = b["match_type"].replace("_", " ")
    adj = f" {b['adjustment']:+d} keyword overlap" if b["adjustment"] else ""
    shared = f" (shared: {', '.join(b['shared_keywords'][:5])})" if b["shared_keywords"] else ""
    out.append({"text": f"Match: {match}, {b['base_score']} base{adj}{shared} = {b['final_score']}", "source": "rule", "points": b["final_score"]})
    return out


def sacrifice_evidence(sac: dict) -> list[dict]:
    prior = sac["breakdown"]["prior_role"]
    if not prior["title"]:
        return [{"text": "No prior role found before the founding role", "source": "profile", "points": 0}]
    src = prior["score_source"]
    if src.startswith("registry_tier_"):
        why = f"registry tier {prior['matched_tier']} company"
    elif src.startswith("unknown_level_"):
        why = f"level {prior['level']} title outside the registry"
    else:
        why = "neither a registry company nor a VP/C-level title"
    return [{"text": f"Left {prior['title']} at {prior['company']} ({why}): {sac['sacrifice_score']}", "source": "profile", "points": sac["sacrifice_score"]}]


def advice(scores: dict[str, float], df: dict) -> list[str]:
    tips = []
    if scores["domain_fit"] < 10:
        c_tag = _tag(df["breakdown"].get("company_tags") or {})
        tips.append(
            f"Your background barely overlaps with {c_tag}. Expect \"why you?\" early in every pitch; "
            "have a concrete answer (customers you've worked with, data you have, a problem you lived)."
        )
    if df["breakdown"].get("company_evidence_level") in {"weak", "name_only"}:
        tips.append("The company description is thin, so its domain was read with low confidence. Two or three sentences on who pays and for what would change that.")
    if scores["seen_greatness"] == 0:
        tips.append(
            "None of your employers are in the high-outcome registry. That's most founders; it's one of four signals. "
            "Make up for it with evidence of speed: what you shipped, how fast, and for whom."
        )
    if scores["horsepower"] < 15:
        tips.append("Your title history reads flat or junior. Titles undersell scope; put team size, systems owned, and results in the deck.")
    if scores["sacrifice"] == 0:
        tips.append("No senior role was given up to start this. Commitment (full time, personal capital) is worth stating plainly.")
    total = sum(scores[k] for k in ("seen_greatness", "horsepower", "domain_fit", "sacrifice"))
    if total >= STRONG:
        tips.append("On paper this clears the partner-review bar. The next questions are about evidence: paying customers, retention, and a sharp wedge.")
    return tips


async def evaluate_founder(
    profile: dict,
    company: dict | None,
    *,
    classifier: DomainClassifier,
    as_of: date,
) -> dict:
    """Score one founder as of a given date. `company`: {name, description, industry,
    raise_amount, raise_date}. The date is required: timing depends on it."""
    as_of_dt = datetime.combine(as_of, datetime.min.time()) if not isinstance(as_of, datetime) else as_of
    sg_scorer = SeenGreatnessScorer()
    sg = sg_scorer.score(profile)
    matched_categories = sg_scorer.matched_categories(profile)

    company = company or None
    entity = (company or {}).get("name")
    founder_tags = await classifier.classify_founder(profile, matched_categories, entity)
    company_tags = await classifier.classify_company(company, company_evidence_level(company)) if company else {}
    df = DomainFitScorer().score(profile, company, founder_tags, company_tags)
    hp = HorsepowerScorer().score(profile, company_tags=company_tags)
    sac = SacrificeScorer().score(profile, filing={"entity_name": entity} if entity else None)
    filing = None
    if company and (company.get("raise_date") or company.get("raise_amount")):
        filing = {"signature_date": company.get("raise_date"), "total_amount_sold": company.get("raise_amount")}
    person = {**profile, "current_title": profile.get("current_title") or next((get_title(e) for e in get_experience(profile)[:1]), "")}
    timing = TimingScorer().score(person, filing, as_of=as_of_dt)

    scores = {
        "seen_greatness": sg["seen_greatness_score"],
        "horsepower": hp["hp_score"],
        "domain_fit": df["domain_fit_score"],
        "sacrifice": sac["sacrifice_score"],
        "timing": timing["timing_score"],
    }
    composite = round(sum(scores[k] for k in ("seen_greatness", "horsepower", "domain_fit", "sacrifice")), 2)
    evidence = {
        "seen_greatness": seen_greatness_evidence(sg),
        "horsepower": horsepower_evidence(hp),
        "domain_fit": domain_fit_evidence(df),
        "sacrifice": sacrifice_evidence(sac),
        "timing": [{"text": s, "source": "rule", "points": None} for s in timing["timing_signals"]]
        or [{"text": "No raise date or amount given" if not filing else "No timing signals", "source": "rule", "points": 0}],
    }
    signals = [
        {
            "key": key,
            "label": LABELS[key],
            "score": round(scores[key], 2),
            "max": MAXIMA[key],
            "percent": round(100 * scores[key] / MAXIMA[key], 1),
            "in_composite": key != "timing",
            "evidence": evidence[key],
        }
        for key in MAXIMA
    ]
    return {
        "engine": ENGINE,
        "classifier": {
            "name": classifier.name,
            "founder_source": founder_tags.get("source"),
            "company_source": company_tags.get("source") if company else None,
        },
        "as_of": as_of_dt.date().isoformat(),
        "founder": {"name": profile.get("name") or "", "synthetic": bool(profile.get("synthetic"))},
        "company": company,
        "composite": {"score": composite, "max": 100, **verdict(composite)},
        "signals": signals,
        "advice": advice(scores, df),
        "tags": {"founder": founder_tags, "company": company_tags},
        "breakdown": {"seen_greatness": sg["breakdown"], "horsepower": hp["breakdown"], "domain_fit": df["breakdown"], "sacrifice": sac["breakdown"]},
    }
