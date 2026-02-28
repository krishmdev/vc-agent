"""Domain tags for founders and companies, in sierra-demo's taxonomy (data/domain_taxonomy.json).

Two classifiers produce the same tag shape:

- GeminiDomainClassifier (live): sierra-demo's prompt and validation, run on gemini-2.5-flash.
  If the call or the JSON fails, it falls back to the keyword classifier and says so, instead of
  sierra-demo's silent "other".
- RecordedDomainClassifier (offline): replays Gemini classifications recorded for the sample
  founders, keyed by sha256 of the exact classifier input, and uses the keyword classifier on a
  miss.
- KeywordDomainClassifier: deterministic phrase matching against a lexicon for each
  (domain, subdomain). Cruder than the model; every tag names the phrases that caused it.

Tags: {primary_domain, primary_subdomain, secondary_subdomains, keywords, reason,
classification_confidence, source}, where source is gemini, recorded, keyword or
fallback_error.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import cache
from pathlib import Path
from typing import Any, Protocol

from .profile import get_company_name, get_degree_name, get_education, get_experience, get_major_text, get_school_name, get_title

DATA_DIR = Path(__file__).resolve().parent / "data"

OTHER_TAGS = {
    "primary_domain": "other",
    "primary_subdomain": "",
    "secondary_subdomains": [],
    "keywords": [],
    "reason": "unclassified",
    "classification_confidence": "low",
}

_LEGAL_SUFFIXES = {"inc", "incorporated", "corp", "corporation", "co", "company", "llc", "ltd", "limited", "plc", "holdings", "holding"}


@cache
def taxonomy() -> dict:
    return json.loads((DATA_DIR / "domain_taxonomy.json").read_text())


def _normalize_company_name(name: str) -> str:
    text = re.sub(r"[^a-z0-9& ]+", " ", (name or "").lower())
    return " ".join(t for t in text.split() if t and t not in _LEGAL_SUFFIXES)


def is_same_company(company_name: str, entity_name: str) -> bool:
    co, en = _normalize_company_name(company_name), _normalize_company_name(entity_name)
    if not co or not en:
        return False
    if co == en:
        return True
    return len(co) >= 5 and len(en) >= 5 and (co in en or en in co)


def founder_input_text(profile: dict, matched_categories: list[dict] | None, entity_name: str | None) -> str:
    """The text both classifiers see for a founder (sierra-demo's format)."""
    roles = [
        f"- {get_title(exp)} at {get_company_name(exp)}"
        for exp in get_experience(profile)
        if not (entity_name and is_same_company(get_company_name(exp), entity_name))
    ]
    edu = [
        f"- {line}"
        for line in (
            f"{get_degree_name(e)} {get_major_text(e)} at {get_school_name(e)}".strip() for e in get_education(profile)
        )
        if line
    ]
    hints = [f"- {c['company']}: {c['category']}" for c in matched_categories or [] if c.get("company") and c.get("category")]
    return "\n".join(
        ["Founder roles:", *(roles or ["- none"]), "Education:", *(edu or ["- none"]), "Known company categories:", *(hints or ["- none"])]
    )


def company_input_text(company: dict, evidence_level: str) -> str:
    return "\n".join(
        [
            f"Company name: {company.get('name') or ''}",
            f"Company evidence level: {evidence_level}",
            f"Description: {company.get('description') or ''}",
            f"Industry group: {company.get('industry') or ''}",
        ]
    )


def validate(parsed: Any) -> dict:
    """sierra-demo's validation: drop anything not in the taxonomy."""
    if not isinstance(parsed, dict):
        return dict(OTHER_TAGS)
    domains = taxonomy()["domains"]
    primary = str(parsed.get("primary_domain") or "other")
    sub = str(parsed.get("primary_subdomain") or "")
    if primary not in domains or (primary != "other" and sub not in domains[primary]):
        return dict(OTHER_TAGS)
    secondary = []
    for item in parsed.get("secondary_subdomains") or []:
        if not isinstance(item, dict):
            continue
        d, s = str(item.get("domain") or ""), str(item.get("subdomain") or "")
        if d in domains and d != "other" and s in domains[d]:
            secondary.append({"domain": d, "subdomain": s})
    keywords = [str(kw).strip().lower().replace(" ", "-") for kw in parsed.get("keywords") or [] if str(kw).strip()]
    confidence = str(parsed.get("classification_confidence") or "medium").strip().lower()
    return {
        "primary_domain": primary,
        "primary_subdomain": sub if primary != "other" else "",
        "secondary_subdomains": secondary[:3],
        "keywords": keywords[:8],
        "reason": str(parsed.get("reason") or "").strip()[:80],
        "classification_confidence": confidence if confidence in {"high", "medium", "low"} else "medium",
    }


def low_confidence_company(tags: dict, evidence_level: str) -> dict:
    """sierra-demo doesn't trust a narrow company domain inferred from a name or industry alone."""
    out = dict(OTHER_TAGS)
    out.update(
        reason=f"{evidence_level} evidence",
        evidence_level=evidence_level,
        tentative_tags=tags,
        keywords=tags.get("keywords") or [],
        source=tags.get("source"),
    )
    return out


def input_key(kind: str, input_text: str) -> str:
    return hashlib.sha256(f"{kind}:{input_text}".encode()).hexdigest()


class DomainClassifier(Protocol):
    name: str

    async def classify_founder(self, profile: dict, matched_categories: list[dict] | None, entity_name: str | None) -> dict: ...

    async def classify_company(self, company: dict, evidence_level: str) -> dict: ...


# Phrases per (domain, subdomain). Matched as whole words in lowercase text with hyphens as spaces.
LEXICON: dict[tuple[str, str], tuple[str, ...]] = {
    ("ai-ml", "foundation-models"): ("foundation model", "large language model", "llm", "pretraining", "generative ai"),
    ("ai-ml", "ml-ops"): ("mlops", "ml ops", "model deployment", "model monitoring"),
    ("ai-ml", "ml-infra"): ("machine learning", "ml engineer", "ml infrastructure", "training infrastructure", "gpu", "inference"),
    ("ai-ml", "computer-vision"): ("computer vision", "image recognition", "vision model", "object detection"),
    ("ai-ml", "nlp"): ("nlp", "natural language", "speech recognition", "language model"),
    ("ai-ml", "reinforcement-learning"): ("reinforcement learning",),
    ("ai-ml", "agentic-ai"): ("ai agent", "ai agents", "agentic", "autonomous agent"),
    ("data-infra", "warehouse"): ("data warehouse", "warehouse", "analytics engineer", "sql"),
    ("data-infra", "etl"): ("etl", "data pipeline", "data pipelines", "data engineer", "data engineering"),
    ("data-infra", "observability"): ("observability", "monitoring", "telemetry", "logging"),
    ("data-infra", "streaming"): ("streaming", "kafka", "real time data"),
    ("data-infra", "lakehouse"): ("lakehouse", "data lake"),
    ("data-infra", "vector-db"): ("vector database", "vector search", "embeddings"),
    ("devtools", "ide"): ("ide", "code editor"),
    ("devtools", "language"): ("programming language", "compiler", "compilers"),
    ("devtools", "framework"): ("framework", "sdk", "open source library"),
    ("devtools", "ci-cd"): ("ci cd", "continuous integration", "build system", "release engineering"),
    ("devtools", "devx"): ("developer experience", "developer tools", "developer platform", "api"),
    ("devtools", "low-code"): ("low code", "no code"),
    ("security", "appsec"): ("application security", "appsec", "security engineer"),
    ("security", "identity"): ("identity", "authentication", "access management", "sso"),
    ("security", "network-sec"): ("network security", "firewall", "zero trust"),
    ("security", "sast"): ("static analysis", "vulnerability scanning"),
    ("security", "compliance"): ("compliance", "soc 2", "hipaa", "audit"),
    ("security", "cloud-sec"): ("cloud security",),
    ("cloud-infra", "kubernetes"): ("kubernetes", "k8s", "containers", "container orchestration"),
    ("cloud-infra", "serverless"): ("serverless", "functions as a service"),
    ("cloud-infra", "edge"): ("edge computing", "edge"),
    ("cloud-infra", "cdn"): ("cdn", "content delivery"),
    ("cloud-infra", "multicloud"): ("multicloud", "multi cloud", "cloud infrastructure", "aws", "azure"),
    ("cloud-infra", "platform-eng"): ("platform engineering", "platform engineer", "site reliability", "sre", "infrastructure engineer", "distributed systems"),
    ("hardware", "semiconductors"): ("semiconductor", "semiconductors", "chip", "chips", "asic", "fpga", "silicon"),
    ("hardware", "iot"): ("iot", "internet of things", "connected devices", "sensors"),
    ("hardware", "wearables"): ("wearable", "wearables"),
    ("hardware", "electronics"): ("electronics", "pcb", "circuit", "circuits", "electrical engineering", "hardware engineer", "hardware design", "hardware startups", "hardware"),
    ("hardware", "embedded"): ("embedded", "firmware", "microcontroller"),
    ("telecom", "5g"): ("5g", "wireless", "radio"),
    ("telecom", "voice"): ("voip", "telephony"),
    ("telecom", "connectivity"): ("connectivity", "broadband", "networking"),
    ("telecom", "satellite-comms"): ("satellite communications", "satcom"),
    ("space-aerospace", "satellites"): ("satellite", "satellites", "spacecraft"),
    ("space-aerospace", "launch"): ("launch vehicle", "rocket", "rockets", "propulsion"),
    ("space-aerospace", "space-resources"): ("space resources", "in space manufacturing"),
    ("space-aerospace", "defense-tech"): ("defense", "defense tech", "aerospace", "avionics"),
    ("fintech", "payments"): ("payments", "payment", "billing", "split bills", "splits", "bill splitting", "shared expenses", "utility bills", "settle up", "settles up", "money transfer", "venmo"),
    ("fintech", "banking"): ("banking", "bank", "neobank", "checking account"),
    ("fintech", "lending"): ("lending", "loans", "credit", "underwriting"),
    ("fintech", "crypto"): ("crypto", "blockchain", "web3"),
    ("fintech", "insurance"): ("insurance", "insurance claims", "claims", "insurtech", "pet insurance"),
    ("fintech", "fraud"): ("fraud", "risk scoring", "kyc", "aml"),
    ("fintech", "wealth"): ("wealth management", "investing", "brokerage"),
    ("healthcare", "clinical-trials"): ("clinical trial", "clinical trials"),
    ("healthcare", "ehr"): ("ehr", "electronic health record", "medical records", "practice management", "patient records"),
    ("healthcare", "genomics"): ("genomics", "sequencing", "genetics"),
    ("healthcare", "drug-discovery"): ("drug discovery", "therapeutics", "pharma"),
    ("healthcare", "medical-imaging"): ("medical imaging", "radiology"),
    ("healthcare", "digital-health"): ("digital health", "telehealth", "clinic", "clinics", "veterinary", "veterinarian", "patients", "hospital", "health"),
    ("healthcare", "bio-tools"): ("lab automation", "bioinformatics", "biotech"),
    ("robotics", "industrial"): ("industrial robotics", "manufacturing automation", "robot arm"),
    ("robotics", "autonomous-vehicles"): ("autonomous vehicles", "self driving", "autonomy"),
    ("robotics", "drones"): ("drone", "drones", "uav"),
    ("robotics", "surgical"): ("surgical robot", "surgical robotics"),
    ("robotics", "humanoid"): ("humanoid",),
    ("quantum", "quantum-hardware"): ("quantum hardware", "qubit", "qubits"),
    ("quantum", "quantum-software"): ("quantum software", "quantum computing", "quantum algorithms"),
    ("quantum", "quantum-sensing"): ("quantum sensing",),
    ("quantum", "error-correction"): ("error correction",),
    ("enterprise-saas", "hr"): ("hr", "recruiting", "payroll", "workforce"),
    ("enterprise-saas", "sales-ops"): ("sales", "crm", "revenue operations", "sales ops"),
    ("enterprise-saas", "finance-ops"): ("accounting", "invoicing", "expense", "bookkeeping", "finance operations", "reconciliation"),
    ("enterprise-saas", "legal"): ("legal", "contracts", "law firm"),
    ("enterprise-saas", "marketing-ops"): ("marketing", "growth marketing", "appointment reminders", "customer engagement"),
    ("enterprise-saas", "procurement"): ("procurement", "purchasing", "inventory", "inventory reordering", "supplier"),
    ("enterprise-saas", "proptech"): ("real estate", "property management", "rent", "landlord", "leasing"),
    ("enterprise-saas", "logistics-supply-chain"): ("logistics", "supply chain", "shipping", "warehouse operations"),
    ("consumer", "social"): ("social network", "social app", "community"),
    ("consumer", "gaming"): ("gaming", "game", "games"),
    ("consumer", "edtech"): ("edtech", "education", "students", "college students", "learning"),
    ("consumer", "marketplace"): ("marketplace", "two sided marketplace", "matches", "matching", "freelance"),
    ("consumer", "creator-tools"): ("creator", "creators", "content creation"),
    ("consumer", "wellness"): ("wellness", "fitness", "mental health"),
    ("climate-energy", "carbon"): ("carbon", "emissions", "carbon capture"),
    ("climate-energy", "batteries"): ("battery", "batteries", "energy storage"),
    ("climate-energy", "grid"): ("grid", "solar", "utilities", "power systems"),
    ("climate-energy", "agtech"): ("agtech", "agriculture", "farming"),
    ("climate-energy", "materials"): ("materials science", "advanced materials"),
}

# sierra-demo registry categories -> taxonomy domain, used as founder-side hints.
CATEGORY_DOMAINS = {
    "ai/ml": "ai-ml", "data/analytics": "data-infra", "fintech": "fintech", "enterprise saas": "enterprise-saas",
    "security": "security", "developer tools": "devtools", "health/biotech": "healthcare", "consumer": "consumer",
    "climate/energy": "climate-energy", "marketplace": "consumer", "cloud/infrastructure": "cloud-infra",
    "devops": "devtools", "crypto/web3": "fintech", "communication": "telecom", "space": "space-aerospace",
    "real estate": "enterprise-saas", "robotics": "robotics", "hr/workforce": "enterprise-saas", "education": "consumer",
}

_PATTERNS = {
    pair: [(p, re.compile(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])")) for p in phrases]
    for pair, phrases in LEXICON.items()
}


def _text(value: str) -> str:
    return " " + re.sub(r"[^a-z0-9$ ]+", " ", value.lower().replace("-", " ")) + " "


class KeywordDomainClassifier:
    name = "keyword-lexicon"

    def tags_for_text(self, text: str, domain_hints: dict[str, int] | None = None) -> dict:
        haystack = _text(text)
        matched: dict[tuple[str, str], list[str]] = {}
        for pair, patterns in _PATTERNS.items():
            # Overlapping matches count once, longest first: "pet insurance claims" is one hit for
            # fintech/insurance, not insurance + claims + pet insurance + insurance claims.
            spans = sorted(
                ((m.start(), m.end(), phrase) for phrase, rx in patterns for m in rx.finditer(haystack)),
                key=lambda s: s[0] - s[1],
            )
            taken: list[tuple[int, int]] = []
            hits: list[str] = []
            for start, end, phrase in spans:
                if any(start < e and s < end for s, e in taken):
                    continue
                taken.append((start, end))
                if phrase not in hits:
                    hits.append(phrase)
            if hits:
                matched[pair] = hits
        if not matched:
            return {**OTHER_TAGS, "source": "keyword"}
        domain_score: dict[str, int] = {}
        for (domain, _), hits in matched.items():
            domain_score[domain] = domain_score.get(domain, 0) + len(hits)
        for domain, weight in (domain_hints or {}).items():
            if domain in domain_score:
                domain_score[domain] += weight
        order = list(LEXICON)
        ranked = sorted(matched, key=lambda p: (-domain_score[p[0]], -len(matched[p]), order.index(p)))
        primary = ranked[0]
        hit_count = sum(len(v) for v in matched.values())
        keywords: list[str] = []
        for pair in ranked:
            for phrase in matched[pair]:
                kw = phrase.replace(" ", "-")
                if kw not in keywords:
                    keywords.append(kw)
        return validate(
            {
                "primary_domain": primary[0],
                "primary_subdomain": primary[1],
                "secondary_subdomains": [{"domain": d, "subdomain": s} for d, s in ranked[1:4]],
                "keywords": keywords[:8],
                "reason": "matched " + ", ".join(matched[primary][:3]),
                "classification_confidence": "high" if hit_count >= 3 else "medium",
            }
        ) | {"source": "keyword"}

    async def classify_founder(self, profile: dict, matched_categories: list[dict] | None, entity_name: str | None) -> dict:
        hints: dict[str, int] = {}
        for item in matched_categories or []:
            domain = CATEGORY_DOMAINS.get(str(item.get("category") or ""))
            if domain:
                hints[domain] = hints.get(domain, 0) + 1
        # Only role and education content; the section headers in founder_input_text ("Education:")
        # would otherwise match the lexicon.
        parts = [
            f"{get_title(exp)} {get_company_name(exp)}"
            for exp in get_experience(profile)
            if not (entity_name and is_same_company(get_company_name(exp), entity_name))
        ]
        parts += [f"{get_degree_name(e)} {get_major_text(e)} {get_school_name(e)}" for e in get_education(profile)]
        return self.tags_for_text(" ".join(parts), hints)

    async def classify_company(self, company: dict, evidence_level: str) -> dict:
        tags = self.tags_for_text(f"{company.get('name') or ''} {company.get('description') or ''} {company.get('industry') or ''}")
        if evidence_level in {"weak", "name_only"}:
            return low_confidence_company(tags, evidence_level)
        return {**tags, "evidence_level": evidence_level}


def gemini_prompt(kind: str, input_text: str) -> str:
    taxonomy_text = json.dumps(taxonomy()["domains"], indent=2)
    subject = "founder's professional background" if kind == "founder" else "company"
    return f"""You classify a {subject} into our domain taxonomy.

Taxonomy: output exactly these strings, no others:
{taxonomy_text}

Input:
{input_text}

Rules:
- primary_domain: the single domain with the most evidence. Use "other" if none fit.
- primary_subdomain: the most specific subdomain under the primary domain, or "" for other.
- secondary_subdomains: up to 3 other domain/subdomain pairs with meaningful evidence.
- keywords: 4-8 short noun phrases, lowercase, hyphen-joined.
- reason: 1-2 word phrase.
- classification_confidence: "high", "medium", or "low".
- For companies with weak/name_only evidence, do not infer a narrow high-confidence domain from company name alone.

Output strict JSON only:
{{
  "primary_domain": "...",
  "primary_subdomain": "...",
  "secondary_subdomains": [{{"domain": "...", "subdomain": "..."}}],
  "keywords": ["..."],
  "reason": "...",
  "classification_confidence": "..."
}}"""


class GeminiDomainClassifier:
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", client: Any = None) -> None:
        if client is None:
            from google import genai

            client = genai.Client(api_key=api_key)
        self._client = client
        self.model = model
        self.fallback = KeywordDomainClassifier()

    async def classify_text(self, kind: str, input_text: str) -> dict:
        from google.genai import types

        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=gemini_prompt(kind, input_text),
            config=types.GenerateContentConfig(response_mime_type="application/json", max_output_tokens=512),
        )
        parsed = json.loads(response.text or "")
        if not isinstance(parsed, dict):
            raise ValueError("classification is not a JSON object")
        return {**validate(parsed), "source": "gemini", "model": self.model}

    async def classify_founder(self, profile: dict, matched_categories: list[dict] | None, entity_name: str | None) -> dict:
        try:
            return await self.classify_text("founder", founder_input_text(profile, matched_categories, entity_name))
        except Exception as exc:
            tags = await self.fallback.classify_founder(profile, matched_categories, entity_name)
            return {**tags, "source": "fallback_error", "error": f"{type(exc).__name__}: {exc}"[:200]}

    async def classify_company(self, company: dict, evidence_level: str) -> dict:
        try:
            tags = await self.classify_text("company", company_input_text(company, evidence_level))
        except Exception as exc:
            tags = await self.fallback.classify_company(company, "medium")
            tags = {**tags, "source": "fallback_error", "error": f"{type(exc).__name__}: {exc}"[:200]}
        if evidence_level in {"weak", "name_only"}:
            return low_confidence_company(tags, evidence_level)
        return {**tags, "evidence_level": evidence_level}


class RecordedDomainClassifier:
    """Offline: replay recorded Gemini tags on an exact input match, else the keyword lexicon."""

    name = "recorded+keyword"

    def __init__(self, recordings: dict[str, dict]) -> None:
        self.recordings = recordings
        self.fallback = KeywordDomainClassifier()

    @classmethod
    def from_file(cls, path: Path) -> "RecordedDomainClassifier":
        data = json.loads(path.read_text()) if path.exists() else {"recordings": {}}
        return cls(data.get("recordings", {}))

    def _replay(self, kind: str, input_text: str) -> dict | None:
        rec = self.recordings.get(input_key(kind, input_text))
        if not rec:
            return None
        return {**validate(rec["tags"]), "source": "recorded", "model": rec.get("model"), "recorded_at": rec.get("recorded_at")}

    async def classify_founder(self, profile: dict, matched_categories: list[dict] | None, entity_name: str | None) -> dict:
        replayed = self._replay("founder", founder_input_text(profile, matched_categories, entity_name))
        return replayed or await self.fallback.classify_founder(profile, matched_categories, entity_name)

    async def classify_company(self, company: dict, evidence_level: str) -> dict:
        replayed = self._replay("company", company_input_text(company, evidence_level))
        if replayed is None:
            return await self.fallback.classify_company(company, evidence_level)
        if evidence_level in {"weak", "name_only"}:
            return low_confidence_company(replayed, evidence_level)
        return {**replayed, "evidence_level": evidence_level}
