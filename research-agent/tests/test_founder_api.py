"""Founder scorecard endpoints in offline mode."""

import json
from datetime import date

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
    with TestClient(main.app) as c:
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
    assert card["classifier"]["founder_source"] in {"recorded", "keyword"}
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


def test_live_default_date_is_today_offline_is_pinned(monkeypatch):
    assert founder_api.default_as_of() == date.fromisoformat(settings.SCORING_AS_OF)
    monkeypatch.setattr(settings, "OFFLINE", False)
    assert founder_api.default_as_of() == date.today()


def test_recorded_tags_are_used_for_samples_when_present(client):
    recordings = json.loads(founder_api.RECORDINGS.read_text())["recordings"] if founder_api.RECORDINGS.exists() else {}
    if not recordings:
        pytest.skip("no recorded classifications committed")
    card = client.get("/founder/samples/vet-clinic-founder/score").json()
    assert card["classifier"] == {"name": "recorded+keyword", "founder_source": "recorded", "company_source": "recorded"}
    assert card["tags"]["founder"]["model"] and card["tags"]["founder"]["recorded_at"]


def test_non_synthetic_fixture_is_refused(tmp_path, monkeypatch):
    (tmp_path / "real.json").write_text(json.dumps({"id": "real", "name": "Someone", "company": {"name": "X"}}))
    monkeypatch.setattr(founder_api, "FIXTURE_DIR", tmp_path)
    with pytest.raises(RuntimeError, match="not marked synthetic"):
        founder_api.load_samples()
