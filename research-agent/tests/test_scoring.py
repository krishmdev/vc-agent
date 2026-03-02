"""Founder scoring engine.

The first block is sierra-demo's own scorer tests (backend/tests/scoring at sierra-demo commit
c1e4568; synthetic inline profiles), ported to check the port gives the same numbers. The rest covers what's new here: the offline keyword
classifier, evidence and advice, as_of, and the four synthetic fixture founders.
"""

import asyncio
import json
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from scoring import evaluate_founder, verdict
import hashlib
import re

from scoring.classifier import (
    OTHER_TAGS,
    GeminiDomainClassifier,
    KeywordDomainClassifier,
    RecordedDomainClassifier,
    company_input_text,
    input_key,
    validate,
)
from scoring.domain_fit import DomainFitScorer, company_evidence_level
from scoring.horsepower import HorsepowerScorer
from scoring.registry import CompanyRegistry, default_registry
from scoring.sacrifice import SacrificeScorer
from scoring.seen_greatness import SeenGreatnessScorer
from scoring.timing import TimingScorer
from scoring.titles import classify_title

FIXTURES = Path(__file__).resolve().parents[1] / "scoring" / "fixtures"


def run(coro):
    return asyncio.run(coro)


# --- ported from sierra-demo backend/tests/scoring ---------------------------------------------


def test_registry_rejects_short_alias_false_positive():
    registry = CompanyRegistry()
    assert registry.match("FendX Technologies")[0] is None
    assert registry.match("Infleqtion")[0]["name"] == "infleqtion"
    assert registry.match("Inflection AI")[0]["name"] == "inflection ai"
    assert len(registry.companies) == 465


def test_stripe_director_early_score():
    result = SeenGreatnessScorer().score({"experience_json": [{"company": "Stripe", "title": "Director of Engineering", "year_range": "2014-2018"}]})
    assert result["seen_greatness_score"] == pytest.approx(11.5 * 1.5 * 1.18)


def test_stripe_senior_breakout_window_score():
    result = SeenGreatnessScorer().score({"experience_json": [{"company": "Stripe", "title": "Senior Software Engineer", "year_range": "2016-2020"}]})
    assert result["seen_greatness_score"] == pytest.approx(11.5 * 1.0 * 1.08)


def test_late_elite_company_ic_gets_no_earliness_credit():
    result = SeenGreatnessScorer().score({"experience_json": [{"company": "Google", "title": "Machine Learning Engineer", "year_range": "2020-2024"}]})
    best = result["breakdown"]["best_company"]
    assert best["seniority_multiplier"] == 0.6
    assert best["earliness_multiplier"] == pytest.approx(1.0)
    assert result["seen_greatness_score"] == pytest.approx(11.5 * 0.6)


def test_ibm_operations_does_not_qualify_but_research_does():
    scorer = SeenGreatnessScorer()
    ops = scorer.score({"experience_json": [{"company": "IBM", "title": "Director of Operations", "year_range": "2018-2024"}]})
    research = scorer.score({"experience_json": [{"company": "IBM Research", "title": "Research Scientist", "year_range": "2018-2024"}]})
    assert ops["seen_greatness_score"] == 0
    assert research["seen_greatness_score"] > 0


def test_bonuses_apply_once():
    result = SeenGreatnessScorer().score({"experience_json": [
        {"company": "NewCo", "title": "Founder", "year_range": "2024-present"},
        {"company": "OldCo", "title": "Co-Founder", "year_range": "2018-2019"},
        {"company": "SmallCo", "title": "VP Engineering", "year_range": "2020-2023"},
    ]})
    assert result["seen_greatness_score"] == pytest.approx(11.4)
    assert result["breakdown"]["prior_founder_kind"] == "brief"
    assert result["breakdown"]["small_co_builder_bonus"] == 4.0


def test_sustained_and_validated_prior_founder_bonus():
    scorer = SeenGreatnessScorer()
    sustained = scorer.score({"experience_json": [
        {"company": "NewCo", "title": "Founder", "year_range": "2024-present"},
        {"company": "OldCo", "title": "Co-Founder", "year_range": "2015-2020"},
    ]})
    validated = scorer.score({"experience_json": [
        {"company": "NewCo", "title": "Founder", "year_range": "2024-present"},
        {"company": "Stripe", "title": "Co-Founder", "year_range": "2010-2015"},
    ]})
    assert sustained["breakdown"]["prior_founder_kind"] == "sustained"
    assert sustained["seen_greatness_score"] == pytest.approx(8.0)
    assert validated["breakdown"]["prior_founder_kind"] == "validated"
    assert validated["breakdown"]["prior_founder_bonus"] == pytest.approx(14.0)


def test_no_cliff_at_3_year_boundary():
    scorer = SeenGreatnessScorer()
    under = scorer.score({"experience_json": [
        {"company": "NewCo", "title": "Founder", "year_range": "2024-present"},
        {"company": "OldCo", "title": "Co-Founder", "year_range": "2018-2020"},
    ]})
    over = scorer.score({"experience_json": [
        {"company": "NewCo", "title": "Founder", "year_range": "2024-present"},
        {"company": "OldCo", "title": "Co-Founder", "year_range": "2017-2020"},
    ]})
    assert over["seen_greatness_score"] - under["seen_greatness_score"] < 2.0


def test_fast_climb_beats_senior_plateau():
    scorer = HorsepowerScorer()
    fast = scorer.score({"experience_json": [
        {"title": "Software Engineer", "company": "A", "year_range": "2020-2020"},
        {"title": "Senior Engineer", "company": "A", "year_range": "2021-2021"},
        {"title": "Director", "company": "A", "year_range": "2022-2022"},
        {"title": "VP Engineering", "company": "A", "year_range": "2023-2023"},
    ]})
    plateau = scorer.score({"experience_json": [{"title": "Senior Engineer", "company": "B", "year_range": "2010-2023"}]})
    assert fast["hp_weighted_level_score"] == 17
    assert plateau["hp_weighted_level_score"] == 14


@pytest.mark.parametrize(
    ("experience", "level", "points"),
    [
        ([{"title": "Director of Engineering", "company": "SomeCo"}, {"title": "Software Engineer", "company": "AnotherCo"}], 3.25, 15),
        ([{"title": "VP Engineering", "company": "SomeCo"}], 5.0, 21),
    ],
)
def test_sparse_dates_use_unweighted_average(experience, level, points):
    result = HorsepowerScorer().score({"experience_json": experience})
    assert result["hp_weighted_level"] == level
    assert result["hp_weighted_level_score"] == points


@pytest.mark.parametrize(
    ("title", "company", "level", "modifier"),
    [
        ("Machine Learning Engineer", "Google", 2.75, 0.75),
        ("Forward Deployed Engineer", "Palantir", 2.25, 0.25),
        ("Director of Operations", "IBM", 4.0, 0.0),
    ],
)
def test_role_modifiers_are_positive_only(title, company, level, modifier):
    result = HorsepowerScorer().score({"experience_json": [{"title": title, "company": company, "year_range": "2020-2024"}]})
    assert result["hp_weighted_level"] == level
    assert result["breakdown"]["classified_roles"][0]["role_modifier"] == modifier


@pytest.mark.parametrize(
    ("school", "major", "domain", "level", "points", "edu"),
    [
        ("MIT", "Bioengineering", "healthcare", 4.0, 18, 6),
        ("State University", "Bioengineering", "healthcare", 3.5, 16, 5),
        ("State University", "Philosophy", "consumer", 0.0, 0, 5),
    ],
)
def test_phd_synthetic_research_role(school, major, domain, level, points, edu):
    result = HorsepowerScorer().score(
        {"education_json": [{"school": school, "degree": "PhD", "major": major}]}, company_tags={"primary_domain": domain}
    )
    assert result["hp_weighted_level"] == level
    assert result["hp_weighted_level_score"] == points
    assert result["hp_education_bonus"] == edu


def test_postdoc_counts_as_research_leadership():
    result = HorsepowerScorer().score({
        "experience_json": [{"title": "Postdoctoral Research Fellow", "company": "MIT University", "year_range": "2022-2025"}],
        "education_json": [{"school": "MIT", "degree": "PhD", "major": "Bioengineering"}],
    }, company_tags={"primary_domain": "healthcare"})
    assert (result["hp_weighted_level"], result["hp_weighted_level_score"], result["hp_education_bonus"]) == (4.0, 18, 6)


def test_masters_bonus_school_spread():
    scorer = HorsepowerScorer()
    assert scorer.score({"education_json": [{"school": "State University", "degree": "MS"}]})["hp_education_bonus"] == 2
    assert scorer.score({"education_json": [{"school": "Stanford University", "degree": "MS"}]})["hp_education_bonus"] == 4


@pytest.mark.parametrize(
    ("title", "company", "points"),
    [
        ("Director", "Google", 5),
        ("Chief Executive Officer", "ObscureCo", 2),
        ("VP Engineering", "ObscureCo", 1),
        ("Director", "UnknownCo", 0),
        ("Senior Engineer", "UnknownCo", 0),
    ],
)
def test_sacrifice_points(title, company, points):
    result = SacrificeScorer().score({"experience": [
        {"title": "Founder", "company": "NewCo", "year_range": "2024-present"},
        {"title": title, "company": company, "year_range": "2020-2024"},
    ]})
    assert result["sacrifice_score"] == points


def test_title_hierarchy():
    assert classify_title("Senior Vice President of Engineering") == 5
    assert classify_title("Co-Founder & CEO") is None
    assert classify_title("Co-Founder & CEO", include_founder=True) == 6
    assert classify_title("Wizard of Customer Joy") is None


def tags(domain, sub, keywords=(), secondary=()):
    return {"primary_domain": domain, "primary_subdomain": sub, "secondary_subdomains": list(secondary), "keywords": list(keywords)}


@pytest.mark.parametrize(
    ("founder", "company", "base", "final", "match"),
    [
        (tags("ai-ml", "ml-infra"), tags("ai-ml", "ml-infra"), 30, 30, "perfect_match"),
        (tags("ai-ml", "ml-infra", ["fraud-detection"], [{"domain": "fintech", "subdomain": "fraud"}]), tags("fintech", "fraud", ["kyc"]), 24, None, "subdomain_match"),
        (tags("ai-ml", "ml-infra", ["fraud-detection"]), tags("ai-ml", "foundation-models", ["protein-folding"]), 18, 18, "domain_only"),
        (tags("ai-ml", "ml-infra", ["fraud-detection"]), tags("ai-ml", "ml-infra", ["protein-folding"]), 30, 28, "perfect_match"),
        (tags("ai-ml", "ml-infra", ["gpu-inference"]), tags("other", ""), 3, 3, "one_sided_other_floor"),
        (tags("ai-ml", "ml-infra"), tags("data-infra", "warehouse"), 6, 6, "adjacent_domain"),
        (tags("fintech", "payments", ["gpu-inference"]), tags("space-aerospace", "launch", ["gpu-inference"]), 0, 0, "no_overlap"),
    ],
)
def test_domain_comparator_tiers(founder, company, base, final, match):
    result = DomainFitScorer().compare(founder, company)
    assert result["base_score"] == base
    assert result["match_type"] == match
    if final is not None:
        assert result["final_score"] == final


def test_keyword_synonyms_normalize_k8s():
    result = DomainFitScorer().compare(tags("ai-ml", "ml-infra", ["k8s"]), tags("ai-ml", "foundation-models", ["kubernetes"]))
    assert "kubernetes" in result["shared_keywords"]


# --- new in this repo ----------------------------------------------------------------------------


def test_cd_synonym_typo_is_fixed_in_the_copied_data():
    from scoring.domain_fit import synonyms

    assert synonyms()["cd"] == "continuous-deployment"


def test_verdict_bands_at_the_boundaries():
    assert [verdict(x)["band"] for x in (60, 59.99, 45, 44.99)] == ["strong", "secondary", "secondary", "filter"]


def test_company_evidence_levels():
    assert company_evidence_level({"name": "X", "description": "Software that helps small clinics send appointment reminders"}) == "medium"
    assert company_evidence_level({"name": "X", "industry": "Health"}) == "weak"
    assert company_evidence_level({"name": "X"}) == "name_only"


def test_keyword_classifier_ignores_section_headers():
    # founder_input_text has an "Education:" header; it must not tag everyone as consumer/edtech.
    founder = run(KeywordDomainClassifier().classify_founder(
        {"experience": [{"title": "Accountant", "company": "Ledger & Co"}], "education": [{"school": "State University", "degree": "BA", "major": "History"}]},
        None, None,
    ))
    assert founder["primary_domain"] == "other"


def test_keyword_classifier_counts_nested_phrases_once():
    tags_ = KeywordDomainClassifier().tags_for_text("veterinary clinics, appointment reminders and pet insurance claims")
    assert (tags_["primary_domain"], tags_["primary_subdomain"]) == ("healthcare", "digital-health")
    assert "claims" not in tags_["keywords"]  # contained in "insurance claims"


def test_thin_company_is_low_confidence_and_floors_a_current_operator():
    classifier = KeywordDomainClassifier()
    company = {"name": "Gridwise", "industry": "Energy"}
    profile = {"current_title": "Founder & CEO", "current_company": "Gridwise", "experience": [
        {"title": "Founder & CEO", "company": "Gridwise"},
        {"title": "Grid Engineer", "company": "Utility One"},
        {"title": "Solar Analyst", "company": "SunCo"},
    ]}
    founder = run(classifier.classify_founder(profile, None, "Gridwise"))
    company_tags = run(classifier.classify_company(company, company_evidence_level(company)))
    assert company_tags["primary_domain"] == "other" and company_tags["reason"] == "weak evidence"
    result = DomainFitScorer().score(profile, company, founder, company_tags)
    assert result["breakdown"]["match_type"].startswith("weak_company_founder_floor_")


def test_timing_uses_as_of_not_the_clock():
    person = {"current_title": "Founder", "experience": [{"title": "Founder", "end_date": None}]}
    filing = {"signature_date": "2026-08-20", "total_amount_sold": 650000}
    early = TimingScorer().score(person, filing, as_of=datetime(2026, 9, 1))
    late = TimingScorer().score(person, filing, as_of=datetime(2027, 9, 1))
    assert early["timing_score"] == 15.0  # 10 fresh + 2 seed range + 3 founding title
    assert late["timing_score"] == 5.0


def fake_client(text=None, delay=0.0, calls=None):
    async def generate_content(**kwargs):
        if calls is not None:
            calls.append(kwargs)
        if delay:
            await asyncio.sleep(delay)
        return NS(text=text)
    return NS(aio=NS(models=NS(generate_content=generate_content)))


def test_gemini_classifier_validates_and_labels_failures():
    calls = []
    good = GeminiDomainClassifier("k", client=fake_client(json.dumps({
        "primary_domain": "fintech", "primary_subdomain": "payments",
        "secondary_subdomains": [{"domain": "made-up", "subdomain": "x"}], "keywords": ["Split Bills"], "classification_confidence": "high",
    }), calls=calls))
    tags_ = run(good.classify_company({"name": "Splitsy", "description": "An app that splits rent and bills between roommates each month"}, "medium"))
    assert (tags_["primary_domain"], tags_["secondary_subdomains"], tags_["keywords"], tags_["source"]) == ("fintech", [], ["split-bills"], "gemini")
    assert "Output strict JSON only" in calls[0]["contents"]
    config = calls[0]["config"]
    assert config.temperature == 0.1 and config.thinking_config.thinking_budget == 0  # sierra's flash settings

    founder = {"experience": [{"title": "Hardware Engineer", "company": "X"}]}
    bad_json = run(GeminiDomainClassifier("k", client=fake_client("not json")).classify_founder(founder, None, None))
    # No silent "other": the keyword classifier answers and the tags say why.
    assert bad_json["source"] == "fallback_error" and "JSONDecodeError" in bad_json["error"]
    assert bad_json["primary_domain"] == "hardware"

    off_taxonomy = run(GeminiDomainClassifier("k", client=fake_client(json.dumps({"primary_domain": "biotech", "primary_subdomain": "x"}))).classify_founder(founder, None, None))
    assert off_taxonomy["source"] == "fallback_error" and "out_of_taxonomy biotech/x" in off_taxonomy["error"]

    slow = run(GeminiDomainClassifier("k", client=fake_client("{}", delay=1.0), timeout_s=0.05).classify_founder(founder, None, None))
    assert slow["source"] == "fallback_error" and "TimeoutError" in slow["error"]
    assert validate({"primary_domain": "fintech", "primary_subdomain": "not-a-subdomain"}) == OTHER_TAGS


def test_pro_models_keep_thinking():
    calls = []
    run(GeminiDomainClassifier("k", model="gemini-3.1-pro-preview", client=fake_client("{}", calls=calls)).classify_founder({"experience": []}, None, None))
    assert calls[0]["config"].thinking_config is None


def test_recordings_are_refused_when_missing_or_stale(tmp_path):
    from scoring.classifier import StaleRecordings, recording_header

    with pytest.raises(StaleRecordings, match="missing"):
        RecordedDomainClassifier.from_file(tmp_path / "none.json")
    stale = tmp_path / "stale.json"
    stale.write_text(json.dumps({"header": {**recording_header(), "taxonomy_sha256": "old"}, "recordings": {}}))
    with pytest.raises(StaleRecordings, match="taxonomy_sha256"):
        RecordedDomainClassifier.from_file(stale)
    fresh = tmp_path / "fresh.json"
    fresh.write_text(json.dumps({"header": recording_header(), "recordings": {}}))
    assert RecordedDomainClassifier.from_file(fresh).recordings == {}


def test_recorded_classifier_replays_exact_inputs_only():
    company = {"name": "Splitsy", "description": "An app that splits rent and bills between roommates each month"}
    key = input_key("company", company_input_text(company, "medium"))
    recorded = RecordedDomainClassifier({key: {
        "tags": {"primary_domain": "fintech", "primary_subdomain": "payments", "keywords": ["bill-splitting"]},
        "model": "gemini-2.5-flash", "recorded_at": "2026-03-01",
    }})
    hit = run(recorded.classify_company(company, "medium"))
    assert (hit["source"], hit["primary_subdomain"], hit["model"]) == ("recorded", "payments", "gemini-2.5-flash")
    miss = run(recorded.classify_company({**company, "description": company["description"] + "."}, "medium"))
    assert miss["source"] == "keyword"


def test_scoring_package_never_reads_the_clock():
    for path in (Path(__file__).resolve().parents[1] / "scoring").glob("*.py"):
        code = path.read_text()
        assert not re.search(r"\.(now|today|utcnow)\(", code), path.name


SIERRA_DATA_SHA256 = {
    # sierra-demo c1e4568 backend/high_outcome_companies.json and backend/data/*.json
    "high_outcome_companies.json": "10dc77d0693dfcd42c68f1c02b477f429c88e35c0a1b5ef033946dcb7b56d825",
    "domain_taxonomy.json": "01af6fc1a6b302f9dd69a24911d248e9221bb75e6c45c857ef878bae34d88e94",
    # keyword_synonyms.json differs from sierra's 1b4680... only by the "cd" backtick fix.
    "keyword_synonyms.json": "c621e00681805e297ad6c8072207ed5a26a210bdea8016ace000afb01ebf32f0",
}


def test_copied_data_matches_the_stamped_sierra_files():
    data = Path(__file__).resolve().parents[1] / "scoring" / "data"
    for name, digest in SIERRA_DATA_SHA256.items():
        assert hashlib.sha256((data / name).read_bytes()).hexdigest() == digest, name


def load(fixture_id):
    return json.loads((FIXTURES / f"{fixture_id}.json").read_text())


def score_fixture(fixture_id):
    fx = load(fixture_id)
    return run(evaluate_founder(fx, fx["company"], classifier=KeywordDomainClassifier(), as_of=date.fromisoformat(fx["as_of"])))


def test_fixtures_are_marked_synthetic():
    for path in FIXTURES.glob("*.json"):
        fx = json.loads(path.read_text())
        assert fx["synthetic"] is True and "Fictional" in fx["note"]


def test_hardware_founder_numbers_trace_to_the_registry():
    r = score_fixture("hardware-reviews-founder")
    sg = {s["key"]: s for s in r["signals"]}
    # Anduril director joined 2019, inflection 2021: 10 x 1.5 x 1.18 = 17.7.
    # SpaceX hardware engineer joined 2012 = inflection year: 11.5 x 0.6 x 1.08 = 7.452.
    # Prior co-founder Sep 2016 - Dec 2018 = 28 months: 5 + 1.2 x 28/12 = 7.8.
    assert sg["seen_greatness"]["score"] == pytest.approx(17.7 + 7.452 + 7.8, abs=0.01)
    assert sg["domain_fit"]["score"] == 30
    assert sg["sacrifice"]["score"] == 4  # left Anduril (tier 1)
    assert r["composite"]["score"] == pytest.approx(87.95, abs=0.01)
    assert (r["composite"]["band"], r["composite"]["thresholds"]) == ("strong", {"strong": 60.0, "secondary": 45.0})
    texts = [e["text"] for e in sg["seen_greatness"]["evidence"]]
    assert texts[0].startswith("Anduril (tier 1, inflection 2021): Director of Hardware Engineering, joined 2019. 10 base x 1.5 seniority x 1.18 earliness = 17.7")


KEYWORD_PATH = {
    # Offline keyword-lexicon path only. The API's offline samples use recorded Gemini tags instead,
    # pinned in test_founder_api.py.
    "vet-clinic-founder": (60.7, "strong"),
    "hardware-reviews-founder": (87.95, "strong"),
    "roommate-bills-founder": (15.1, "filter"),
    "career-switch-founder": (52.25, "secondary"),
}


@pytest.mark.parametrize(("fixture_id", "expected"), KEYWORD_PATH.items())
def test_keyword_path_composites_are_pinned(fixture_id, expected):
    r = score_fixture(fixture_id)
    assert (r["composite"]["score"], r["composite"]["band"]) == (pytest.approx(expected[0], abs=0.01), expected[1])
    assert r["classifier"]["founder_source"] == "keyword"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("Team Rubicon", None), ("team", None), ("TEAM", "atlassian"), ("Open Road", None), ("OPEN", "opendoor"),
     ("bird", None), ("frog", None), ("JFrog", "jfrog"), ("Segment", "segment"), ("Twilio Segment", "twilio segment")],
)
def test_ticker_aliases_need_capitals_and_names_beat_aliases(raw, expected):
    matched, _, _ = CompanyRegistry().match(raw)
    assert (matched["name"] if matched else None) == expected


@pytest.mark.parametrize(
    "school",
    ["Smith College", "Penn State University", "University of British Columbia", "Columbia College Chicago", "Cornell College",
     "Harvard Extension School", "Stanford Online", "Northeastern University", "University"],
)
def test_school_lookalikes_are_not_founder_schools(school):
    assert HorsepowerScorer().score({"education": [{"school": school, "degree": "MS"}]})["hp_education_bonus"] == 2


@pytest.mark.parametrize("school", ["MIT", "Stanford University", "Harvard Business School", "University of California, Berkeley", "IIT Bombay"])
def test_listed_schools_and_aliases_are_founder_schools(school):
    assert HorsepowerScorer().score({"education": [{"school": school, "degree": "MS"}]})["hp_education_bonus"] == 4


def test_future_raise_date_is_not_fresh():
    person = {"current_title": "Engineer", "experience": []}
    result = TimingScorer().score(person, {"signature_date": "2026-10-15", "total_amount_sold": 0}, as_of=datetime(2026, 9, 1))
    assert result["timing_score"] == 0 and "future" in result["timing_signals"][0]


def test_ongoing_role_counts_up_to_as_of():
    profile = {"experience": [
        {"title": "VP Engineering", "company": "SmallCo", "start_date": "2020-01"},
        {"title": "Software Engineer", "company": "OtherCo", "start_date": "2018-01", "end_date": "2019-12"},
    ]}
    result = HorsepowerScorer().score(profile, as_of="2025-12")
    # 72 months at level 5 and 24 months at level 2.5 (engineer + 0.5): (360 + 60) / 96 = 4.375
    assert result["hp_date_handling"] == "duration_weighted"
    assert result["hp_weighted_level"] == pytest.approx(4.375)


def test_evidence_uses_the_founders_spelling_of_companies():
    r = run(evaluate_founder(
        {"experience": [{"company": "NewCo", "title": "Founder"}, {"company": "OpenAI", "title": "Research Scientist", "start_date": "2019", "end_date": "2023"}]},
        None, classifier=KeywordDomainClassifier(), as_of=date(2026, 9, 1),
    ))
    assert r["signals"][0]["evidence"][0]["text"].startswith("OpenAI (tier 0")
    assert {s["key"]: s["scored"] for s in r["signals"]} == {"seen_greatness": True, "horsepower": True, "domain_fit": False, "sacrifice": True, "timing": False}


def test_fixture_bands_cover_all_three_outcomes():
    results = {fid: score_fixture(fid) for fid in ("vet-clinic-founder", "hardware-reviews-founder", "roommate-bills-founder", "career-switch-founder")}
    bands = {fid: r["composite"]["band"] for fid, r in results.items()}
    assert bands == {
        "vet-clinic-founder": "strong",
        "hardware-reviews-founder": "strong",
        "roommate-bills-founder": "filter",
        "career-switch-founder": "secondary",
    }
    career = {s["key"]: s["score"] for s in results["career-switch-founder"]["signals"]}
    assert career["domain_fit"] == 0 and career["seen_greatness"] > 25  # pedigree without domain overlap
    assert any("barely overlaps" in tip for tip in results["career-switch-founder"]["advice"])


def test_evaluation_is_deterministic_and_self_consistent():
    a, b = score_fixture("vet-clinic-founder"), score_fixture("vet-clinic-founder")
    assert a == b
    composite = sum(s["score"] for s in a["signals"] if s["in_composite"])
    assert a["composite"]["score"] == pytest.approx(composite, abs=0.01)
    assert all(0 <= s["percent"] <= 100 for s in a["signals"])
    assert a["classifier"] == {"name": "keyword-lexicon", "founder_source": "keyword", "company_source": "keyword"}
    assert a["founder"]["synthetic"] is True


def test_default_registry_is_shared():
    assert default_registry() is default_registry()
