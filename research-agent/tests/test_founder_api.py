"""Founder scorecard endpoints in offline mode."""

import json

import pytest
from fastapi.testclient import TestClient

import founder_api
import main
import settings
from scoring.classifier import GeminiDomainClassifier, KeywordDomainClassifier, RecordedDomainClassifier

PROFILE = {
    "name": "Test Founder",
    "current_title": "Founder",
    "experience": [
        {"company": "Ledgerline", "title": "Founder", "start_date": "2026-01"},
        {"company": "Stripe", "title": "Staff Software Engineer", "start_date": "2015-02", "end_date": "2025-11"},
    ],
    "education": [{"school": "Carnegie Mellon University", "degree": "BS", "major": "Computer Science"}],
}
COMPANY = {
    "name": "Ledgerline",
    "description": "Payments and billing software that reconciles invoices for small online stores.",
    "raise_amount": 500000,
    "raise_date": "2026-02-15",
}


@pytest.fixture
def client():
    with TestClient(main.app, base_url="http://127.0.0.1") as c:
        yield c


def test_samples_are_synthetic_and_score_to_known_bands(client):
    samples = client.get("/founder/samples").json()
    assert {s["id"] for s in samples} == {"vet-clinic-founder", "hardware-reviews-founder", "roommate-bills-founder", "career-switch-founder"}
    assert all(s["synthetic"] is True and "Fictional" in s["note"] for s in samples)
    card = client.get("/founder/samples/hardware-reviews-founder/score").json()
    assert card["composite"]["band"] == "strong"
    assert card["as_of"] == "2026-03-01"  # the date stored in the fixture
    assert [s["key"] for s in card["signals"]] == ["seen_greatness", "horsepower", "domain_fit", "sacrifice", "timing"]
    assert [s["in_composite"] for s in card["signals"]] == [True, True, True, True, False]
    assert card["composite"]["score"] == pytest.approx(sum(s["score"] for s in card["signals"] if s["in_composite"]), abs=0.01)
    assert card["founder"] == {"name": "Idris Moncrieff-Hale", "synthetic": True}
    assert card["classifier"] == {"name": "recorded+keyword", "founder_source": "recorded", "company_source": "recorded"}
    assert card["composite"]["thresholds"] == {"strong": 60.0, "secondary": 45.0}
    assert all(s["scored"] for s in card["signals"])
    assert "breakdown" not in card


def test_unknown_sample_is_404(client):
    assert client.get("/founder/samples/nobody/score").status_code == 404


def test_submitted_profile_uses_the_pinned_offline_date(client):
    first = client.post("/founder/score", json={"profile": PROFILE, "company": COMPANY}).json()
    assert first["as_of"] == settings.SCORING_AS_OF
    assert first["founder"]["synthetic"] is False
    assert first["tags"]["company"]["primary_domain"] == "fintech"
    again = client.post("/founder/score", json={"profile": PROFILE, "company": COMPANY}).json()
    assert first == again
    later = client.post("/founder/score", json={"profile": PROFILE, "company": COMPANY, "as_of": "2027-06-01"}).json()
    timing = {s["key"]: s["score"] for s in later["signals"]}["timing"]
    assert later["as_of"] == "2027-06-01" and timing < {s["key"]: s["score"] for s in first["signals"]}["timing"]


def test_profile_without_company_scores_domain_fit_zero(client):
    card = client.post("/founder/score", json={"profile": PROFILE}).json()
    df = next(s for s in card["signals"] if s["key"] == "domain_fit")
    assert df["score"] == 0 and "wasn't scored" in df["evidence"][0]["text"]
    assert card["tags"]["company"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"profile": {**PROFILE, "experience": [{"company": "X", "title": "Y", "start_date": "last spring"}]}},
        {"profile": {**PROFILE, "experience": [{"company": "X", "title": "Engineer"}] * 26}},
        {"profile": {**PROFILE, "name": ""}},
        {"profile": PROFILE, "company": {**COMPANY, "raise_amount": -5}},
    ],
)
def test_bad_input_is_rejected(client, body):
    assert client.post("/founder/score", json=body).status_code == 422


def test_classifier_choice_by_mode(monkeypatch):
    assert isinstance(founder_api.make_domain_classifier(), RecordedDomainClassifier)
    monkeypatch.setattr(settings, "OFFLINE", False)
    monkeypatch.setattr(settings, "gemini_api_key", lambda: None)
    assert isinstance(founder_api.make_domain_classifier(), KeywordDomainClassifier)  # labelled, not a 500
    monkeypatch.setattr(settings, "gemini_api_key", lambda: "test-key")
    assert isinstance(founder_api.make_domain_classifier(), GeminiDomainClassifier)


def test_live_mode_requires_as_of(client, monkeypatch):
    monkeypatch.setattr(settings, "OFFLINE", False)
    resp = client.post("/founder/score", json={"profile": PROFILE, "company": COMPANY})
    assert resp.status_code == 422 and "as_of" in resp.json()["detail"]


# Offline sample scores, using the committed recorded Gemini tags (the keyword-lexicon path is
# pinned separately in test_scoring.py).
RECORDED_PATH = {
    "vet-clinic-founder": (55.7, "secondary"),
    "hardware-reviews-founder": (85.95, "strong"),
    "roommate-bills-founder": (30.1, "filter"),
    "career-switch-founder": (52.25, "secondary"),
}


@pytest.mark.parametrize(("sample_id", "expected"), RECORDED_PATH.items())
def test_recorded_path_sample_scores_are_pinned(client, sample_id, expected):
    card = client.get(f"/founder/samples/{sample_id}/score").json()
    assert card["classifier"]["founder_source"] == "recorded" and card["classifier"]["company_source"] == "recorded"
    assert card["tags"]["founder"]["model"] and card["tags"]["founder"]["recorded_at"]
    assert (card["composite"]["score"], card["composite"]["band"]) == (pytest.approx(expected[0], abs=0.01), expected[1])


def test_offline_startup_fails_without_recordings(monkeypatch, tmp_path):
    from scoring.classifier import StaleRecordings

    monkeypatch.setattr(founder_api, "RECORDINGS", tmp_path / "missing.json")
    with pytest.raises(StaleRecordings):
        founder_api.make_domain_classifier()


def test_experience_order_does_not_change_the_scorecard(client):
    fx = json.loads((founder_api.FIXTURE_DIR / "hardware-reviews-founder.json").read_text())
    profile = {k: fx[k] for k in ("name", "current_title", "experience", "education")}
    company = fx["company"]
    body = {"profile": profile, "company": company, "as_of": fx["as_of"]}
    shuffled = {**body, "profile": {**profile, "experience": list(reversed(profile["experience"]))}}
    assert client.post("/founder/score", json=body).json() == client.post("/founder/score", json=shuffled).json()


@pytest.mark.parametrize(
    "role",
    [
        {"company": "X", "title": "Engineer", "start_date": "2020-13"},
        {"company": "X", "title": "Engineer", "start_date": "2021-02-30"},
        {"company": "X", "title": "Engineer", "start_date": "2022-05", "end_date": "2021-01"},
    ],
)
def test_impossible_dates_are_rejected(client, role):
    assert client.post("/founder/score", json={"profile": {**PROFILE, "experience": [role]}}).status_code == 422


def test_dates_compare_as_periods_not_strings(client):
    # "2020-06" to "2020" is a role inside 2020; the old string comparison refused it.
    role = {"company": "X", "title": "Engineer", "start_date": "2020-06", "end_date": "2020"}
    assert client.post("/founder/score", json={"profile": {**PROFILE, "experience": [role]}}).status_code == 200
    assert founder_api.period_end("2024-02") == founder_api.period_end("2024-02-29")


@pytest.mark.parametrize(
    "body",
    [
        {"profile": {**PROFILE, "experience": [{"company": "X", "title": "CEO", "start_date": "2027-01"}]}},
        {"profile": PROFILE, "company": {"name": "X", "raise_date": "2026-10"}},
    ],
)
def test_dates_after_the_scoring_date_are_refused(client, body):
    r = client.post("/founder/score", json={**body, "as_of": "2026-03-02"})
    assert r.status_code == 422 and "after the scoring date" in r.json()["detail"]


def test_raise_amount_is_capped(client):
    body = {"profile": PROFILE, "company": {"name": "X", "raise_amount": 10**13}}
    assert client.post("/founder/score", json=body).status_code == 422


def test_absurd_as_of_is_rejected(client):
    assert client.post("/founder/score", json={"profile": PROFILE, "as_of": "1850-01-01"}).status_code == 422


def test_non_synthetic_fixture_is_refused(tmp_path, monkeypatch):
    (tmp_path / "real.json").write_text(json.dumps({"id": "real", "name": "Someone", "company": {"name": "X"}}))
    monkeypatch.setattr(founder_api, "FIXTURE_DIR", tmp_path)
    with pytest.raises(RuntimeError, match="not marked synthetic"):
        founder_api.load_samples()


def test_undated_founding_role_is_the_current_role(client):
    roles = [
        {"company": "Stripe", "title": "Staff Software Engineer", "start_date": "2015-02", "end_date": "2025-11"},
        {"company": "Ledgerline", "title": "Founder & CEO"},  # typed without dates
    ]
    card = client.post("/founder/score", json={"profile": {**PROFILE, "experience": roles}, "company": COMPANY}).json()
    sg = next(s for s in card["signals"] if s["key"] == "seen_greatness")
    sac = next(s for s in card["signals"] if s["key"] == "sacrifice")
    assert not any("Prior founder" in e["text"] for e in sg["evidence"])  # not a prior founding
    assert sac["score"] == 5  # left Stripe (tier 0) to found Ledgerline
