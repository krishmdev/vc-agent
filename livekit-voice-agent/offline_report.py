"""Post-call VC report without a model, for offline mode.

Same JSON shape as the Gemini report in mentor.py. Every field is copied or selected from what
the founder actually typed; nothing is invented. Dimensions the founder never touched become
gaps, and the matching "terrifying questions" from the VC persona are listed as unanswered.
"""

from textutil import sentences, tokens

DIMENSIONS = {
    "unique-insight": ("insight", {"insight", "secret", "unique", "know", "noticed", "realized"}),
    "why-you": ("founder fit", {"i", "worked", "experience", "background", "years", "built", "founder"}),
    "why-now": ("timing", {"now", "today", "recently", "changed", "shift", "new", "ai"}),
    "hair-on-fire": ("urgency of the problem", {"problem", "pain", "hours", "lose", "losing", "cost", "waste", "frustrated"}),
    "workarounds": ("current workarounds", {"spreadsheet", "manual", "manually", "today", "currently", "workaround", "paper"}),
    "high-expectation-customer": ("the first customer", {"customer", "customers", "clinics", "users", "students", "startups", "buyers"}),
    "wedge": ("the product wedge", {"start", "first", "wedge", "feature", "mvp", "launch"}),
    "path-to-revenue": ("how it makes money", {"$", "price", "pricing", "charge", "month", "subscription", "revenue", "fee"}),
}

UNANSWERED = {
    "hair-on-fire": "Who is desperate enough to pay for this today, and how do you know?",
    "why-you": "Why are you the one to build this?",
    "path-to-revenue": "Can you chart a path to $100M in revenue with these unit economics?",
    "high-expectation-customer": "Who exactly is the first customer, by name or role?",
    "why-now": "What changed in the last two years that makes this possible now?",
}


def _match(sentence: str, words: set[str]) -> int:
    toks = set(tokens(sentence)) | ({"$"} if "$" in sentence else set())
    return len(toks & words)


def offline_report(chat_history: list[dict[str, str]], idea: str | None = None) -> dict:
    said = [s for m in chat_history if m["role"] == "founder" for s in sentences(m["content"])]
    extraction, covered = {}, []
    for field, (label, words) in DIMENSIONS.items():
        best = max(said, key=lambda s: _match(s, words), default=None)
        if best and _match(best, words) > 0:
            extraction[field] = best
            covered.append(label)
        else:
            extraction[field] = ""
    missing = [f for f in DIMENSIONS if not extraction[f]]

    strengths = [f"You were specific about {label}." for label in covered[:3]] or [
        "You showed up to pitch, which is where every company starts."
    ]
    gaps = [f"Nothing yet on {DIMENSIONS[f][0]}." for f in missing][:5]
    subject = f' for "{idea}"' if idea else ""
    diagnosis = (
        f"Offline summary{subject}, built from your own words without a model: you covered "
        f"{len(covered)} of {len(DIMENSIONS)} areas a Sequoia partner probes."
    )
    return {
        "diagnosis": diagnosis,
        "strengths": strengths,
        "gaps": gaps or ["Pressure-test each claim with customer evidence."],
        "terrifyingQuestions": [UNANSWERED[f] for f in missing if f in UNANSWERED][:3]
        or ["What is the assumption that, if wrong, breaks everything?"],
        "nextSteps": [
            "Talk to five target customers this week and write down their exact words.",
            "Put a price in front of them and see who says yes.",
            "Re-run this pitch in live mode for a full model-written report.",
        ],
        "extraction": extraction,
    }
