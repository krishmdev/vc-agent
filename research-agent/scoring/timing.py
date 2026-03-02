"""Timing (0-15): is this a fresh, pre-seed founder? Ported from sierra-demo's timing_scorer.

Recent raise (up to 10), a small raise (up to 3), a founding title (3), and a prior role that
ended in the last six months (2). Not part of the 0-100 composite, same as in sierra-demo; it's
shown separately. The caller passes `as_of` (sierra-demo read the wall clock) so a score is
reproducible.
"""

import json
import re
from datetime import datetime


STEALTH_TITLE_KEYWORDS = ["stealth", "founder", "building", "ceo & founder"]


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    s = str(date_str).strip()
    for fmt, length in (("%Y-%m-%d", 10), ("%Y-%m", 7), ("%Y", 4)):
        try:
            return datetime.strptime(s[:length], fmt)
        except (ValueError, IndexError):
            continue
    match = re.search(r"(\d{4})", s)
    if match:
        return datetime(int(match.group(1)), 6, 1)
    return None


class TimingScorer:

    def score(self, person: dict, filing: dict | None, *, as_of: datetime) -> dict:
        if filing is None:
            return {"timing_score": 0.0, "timing_signals": []}

        points = 0.0
        signals: list[str] = []
        now = as_of

        # --- Signature recency (up to +10) ---
        sig_date = _parse_date(filing.get("signature_date"))
        if sig_date:
            days_ago = (now - sig_date).days
            if days_ago < 0:
                signals.append(f"Raise dated {-days_ago}d in the future; not counted")
            elif days_ago <= 30:
                points += 10
                signals.append(f"Filing signed {days_ago}d ago (fresh)")
            elif days_ago <= 90:
                points += 6
                signals.append(f"Filing signed {days_ago}d ago (recent)")

        # --- Raise size (up to +3) ---
        try:
            amount = int(filing.get("total_amount_sold") or 0)
        except (ValueError, TypeError):
            amount = 0
        if 0 < amount < 500_000:
            points += 3
            signals.append(f"Small raise (${amount:,}), a pre-seed signal")
        elif 500_000 <= amount <= 1_000_000:
            points += 2
            signals.append(f"Seed-range raise (${amount:,})")

        # --- Current title keywords (+3) ---
        current_title = (person.get("current_title") or "").lower()
        if any(kw in current_title for kw in STEALTH_TITLE_KEYWORDS):
            points += 3
            signals.append(f"Current title signals founding: '{person.get('current_title')}'")

        # --- Most recent experience end within 6 months (+2) ---
        experience = person.get("experience") or person.get("experience_json") or []
        if isinstance(experience, str):
            try:
                experience = json.loads(experience) if experience else []
            except (ValueError, TypeError):
                experience = []
        if isinstance(experience, list) and experience:
            first = experience[0]
            if isinstance(first, dict):
                end = _parse_date(first.get("end_date"))
                if end:
                    months_ago = (now - end).days / 30.0
                    if 0 <= months_ago <= 6:
                        points += 2
                        signals.append(f"Left prior role ~{int(months_ago)}mo ago")

        total = min(points, 15.0)
        return {
            "timing_score": round(total, 1),
            "timing_signals": signals,
        }
