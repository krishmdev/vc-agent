"""Founder scoring, ported from sierra-demo (Krish Maheshwari and Akshay Irudayaraj).

Four bounded signals sum to a raw 0-100 composite: Seen Greatness (35), Horsepower (30), Domain
Fit (30) and Sacrifice (5), with Timing (15) reported separately. The scorer modules keep
sierra-demo's constants and logic; what changed is noted in each module's docstring. The data
files (high-outcome company registry, domain taxonomy, keyword synonyms) are copied from
sierra-demo, with one fix: the "cd" synonym had a stray backtick.
"""

from .evaluator import evaluate_founder, verdict

__all__ = ["evaluate_founder", "verdict"]
