"""Founder scorecard endpoints (the scoring engine itself is the pure `scoring` package).

    GET  /founder/samples               synthetic sample founders (fictional people)
    GET  /founder/samples/{id}/score    scorecard for a sample, as of its recorded date
    POST /founder/score                 scorecard for a submitted profile

Scoring is synchronous and quick, so these return the scorecard directly instead of going through
the research task queue. The domain classifier is picked at startup: recorded Gemini tags with a
keyword fallback offline, Gemini live, and the keyword lexicon (labelled as such) in live mode
without a key.
"""

import json
from datetime import date
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

import settings
from scoring import evaluate_founder
from scoring.classifier import DomainClassifier, GeminiDomainClassifier, KeywordDomainClassifier, RecordedDomainClassifier

SCORING_DIR = Path(__file__).resolve().parent / "scoring"
FIXTURE_DIR = SCORING_DIR / "fixtures"
RECORDINGS = SCORING_DIR / "recordings" / "classifications.json"

DATE_PATTERN = r"^\d{4}(-\d{2}(-\d{2})?)?$"


def make_domain_classifier() -> DomainClassifier:
    if settings.OFFLINE:
        return RecordedDomainClassifier.from_file(RECORDINGS)
    key = settings.gemini_api_key()
    return GeminiDomainClassifier(key, model=settings.UTILITY_MODEL) if key else KeywordDomainClassifier()


# --- request models ---


class ExperienceIn(BaseModel):
    company: str = Field(..., max_length=160)
    title: str = Field(..., max_length=160)
    start_date: Optional[str] = Field(None, pattern=DATE_PATTERN)
    end_date: Optional[str] = Field(None, pattern=DATE_PATTERN)


class EducationIn(BaseModel):
    school: str = Field(..., max_length=160)
    degree: str = Field("", max_length=80)
    major: str = Field("", max_length=120)


class FounderProfileIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    current_title: Optional[str] = Field(None, max_length=160)
    experience: list[ExperienceIn] = Field(default_factory=list, max_length=25)
    education: list[EducationIn] = Field(default_factory=list, max_length=10)


class CompanyIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    description: str = Field("", max_length=1500)
    industry: str = Field("", max_length=120)
    raise_amount: Optional[int] = Field(None, ge=0)
    raise_date: Optional[str] = Field(None, pattern=DATE_PATTERN)


class ScoreRequest(BaseModel):
    profile: FounderProfileIn
    company: Optional[CompanyIn] = None
    as_of: Optional[date] = None


# --- response models ---

SignalKey = Literal["seen_greatness", "horsepower", "domain_fit", "sacrifice", "timing"]
TagSource = Literal["gemini", "recorded", "keyword", "fallback_error"]


class Evidence(BaseModel):
    text: str
    source: Literal["registry", "profile", "classifier", "rule"]
    points: Optional[float] = None


class Signal(BaseModel):
    key: SignalKey
    label: str
    score: float
    max: int
    percent: float
    in_composite: bool
    evidence: list[Evidence]


class Composite(BaseModel):
    score: float
    max: int
    band: Literal["strong", "secondary", "filter"]
    label: str


class SubdomainRef(BaseModel):
    domain: str
    subdomain: str


class DomainTags(BaseModel):
    primary_domain: str
    primary_subdomain: str
    secondary_subdomains: list[SubdomainRef] = []
    keywords: list[str] = []
    reason: str = ""
    classification_confidence: str = "low"
    source: Optional[TagSource] = None
    model: Optional[str] = None
    recorded_at: Optional[str] = None
    error: Optional[str] = None
    evidence_level: Optional[str] = None


class Tags(BaseModel):
    founder: DomainTags
    company: Optional[DomainTags] = None


class ClassifierInfo(BaseModel):
    name: str
    founder_source: Optional[TagSource] = None
    company_source: Optional[TagSource] = None


class FounderInfo(BaseModel):
    name: str
    synthetic: bool


class Scorecard(BaseModel):
    engine: str
    classifier: ClassifierInfo
    as_of: date
    founder: FounderInfo
    company: Optional[CompanyIn] = None
    composite: Composite
    signals: list[Signal]
    advice: list[str]
    tags: Tags


class SampleFounder(BaseModel):
    id: str
    name: str
    current_title: Optional[str]
    company: CompanyIn
    synthetic: Literal[True]
    note: str


# --- routes ---

router = APIRouter(prefix="/founder", tags=["founder"])


def load_samples() -> dict[str, dict]:
    samples = {}
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        if data.get("synthetic") is not True:
            raise RuntimeError(f"{path.name} is not marked synthetic")
        samples[data["id"]] = data
    return samples


def default_as_of() -> date:
    if settings.OFFLINE:
        return date.fromisoformat(settings.SCORING_AS_OF)
    return date.today()


async def score(request: Request, profile: dict, company: Optional[dict], as_of: date) -> dict:
    tags_company = {k: v for k, v in (company or {}).items() if v not in (None, "")} or None
    result = await evaluate_founder(profile, tags_company, classifier=request.app.state.classifier, as_of=as_of)
    tags = result["tags"]
    if not tags.get("company"):
        tags["company"] = None
    return result


@router.get("/samples", response_model=list[SampleFounder])
async def list_samples():
    return [
        SampleFounder(id=s["id"], name=s["name"], current_title=s.get("current_title"), company=CompanyIn(**s["company"]), synthetic=True, note=s["note"])
        for s in load_samples().values()
    ]


@router.get("/samples/{sample_id}/score", response_model=Scorecard)
async def score_sample(sample_id: str, request: Request):
    sample = load_samples().get(sample_id)
    if sample is None:
        raise HTTPException(status_code=404, detail="No such sample founder")
    return await score(request, sample, sample["company"], date.fromisoformat(sample["as_of"]))


@router.post("/score", response_model=Scorecard)
async def score_profile(body: ScoreRequest, request: Request):
    profile = body.profile.model_dump()
    company = body.company.model_dump() if body.company else None
    return await score(request, profile, company, body.as_of or default_as_of())
