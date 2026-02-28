"""Helpers for reading founder profile payloads (ported from sierra-demo's profile_utils).

Profiles can use flattened fields ("year_range": "2018-2021") or nested PDL-style dicts; these
helpers keep the scorers independent of the shape.
"""

from __future__ import annotations

import json
import re
from typing import Any


def _loads(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        if not value.strip():
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return value


def get_experience(profile: dict) -> list[dict]:
    value = profile.get("experience")
    if value is None:
        value = profile.get("experience_json")
    parsed = _loads(value, [])
    return parsed if isinstance(parsed, list) else []


def get_education(profile: dict) -> list[dict]:
    value = profile.get("education")
    if value is None:
        value = profile.get("education_json")
    parsed = _loads(value, [])
    return parsed if isinstance(parsed, list) else []


def get_title(exp: dict) -> str:
    title = exp.get("title")
    if isinstance(title, dict):
        return str(title.get("name") or "").strip()
    return str(title or exp.get("title_name") or "").strip()


def get_company_name(exp: dict) -> str:
    company = exp.get("company")
    if isinstance(company, dict):
        return str(company.get("name") or "").strip()
    return str(company or exp.get("company_name") or "").strip()


def get_company_size(exp: dict) -> str:
    company = exp.get("company")
    if isinstance(company, dict):
        return str(company.get("size") or "").strip()
    return str(exp.get("company_size") or "").strip()


def get_start_date(exp: dict) -> str | None:
    return _date_from_exp(exp, "start")


def get_end_date(exp: dict) -> str | None:
    return _date_from_exp(exp, "end")


def get_school_name(edu: dict) -> str:
    school = edu.get("school")
    if isinstance(school, dict):
        return str(school.get("name") or "").strip()
    return str(school or edu.get("school_name") or "").strip()


def get_degree_name(edu: dict) -> str:
    degree = edu.get("degree")
    if isinstance(degree, dict):
        return str(degree.get("name") or "").strip()
    degrees = edu.get("degrees")
    if isinstance(degrees, list) and degrees:
        return str(degrees[0] or "").strip()
    return str(degree or "").strip()


def get_major_text(edu: dict) -> str:
    majors = edu.get("majors")
    if isinstance(majors, list):
        return " ".join(str(m) for m in majors if m)
    return str(edu.get("major") or edu.get("field_of_study") or majors or "").strip()


def parse_year(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("year")
    match = re.search(r"(\d{4})", str(value))
    return int(match.group(1)) if match else None


def parse_year_month(value: Any, *, default_month: int = 1) -> tuple[int, int] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        year = value.get("year")
        month = value.get("month") or default_month
        if year:
            return int(year), int(month)
    text = str(value)
    match = re.search(r"(\d{4})(?:[-/](\d{1,2}))?", text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2) or default_month)


def duration_months(start_value: Any, end_value: Any) -> int | None:
    start = parse_year_month(start_value, default_month=1)
    end = parse_year_month(end_value, default_month=12)
    if not start or not end:
        return None
    months = (end[0] - start[0]) * 12 + (end[1] - start[1]) + 1
    return months if months > 0 else None


def is_founder_title(title: str) -> bool:
    t = (title or "").lower()
    return "founder" in t or "co-founder" in t or "cofounder" in t


def _date_from_exp(exp: dict, kind: str) -> str | None:
    direct = exp.get(f"{kind}_date")
    if direct:
        return str(direct)

    # Flattened enrichment stores "2018-2021" or "2024-present".
    yr = str(exp.get("year_range") or "")
    if "-" in yr:
        start, end = yr.split("-", 1)
        value = start if kind == "start" else end
        value = value.strip()
        if value and value.lower() not in {"present", "now", "current", "none", "null", "?"}:
            return value
    return None
