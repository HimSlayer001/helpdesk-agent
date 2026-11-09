"""Input/output safety checks: prompt-injection detection and secret redaction.

Rule-based on purpose: cheap, deterministic, testable, and it runs before anything reaches the LLM.
"""
from __future__ import annotations

import re

INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) (instructions|rules)",
    r"disregard (the |your )?(system|previous) (prompt|instructions)",
    r"you are now (in )?(developer|dan|admin) mode",
    r"reveal (your |the )?(system prompt|hidden instructions)",
    r"act as (an? )?(unrestricted|jailbroken)",
    r"(print|show|dump) (all )?(tickets|passwords|credentials|api keys)",
]

SECRET_PATTERNS = [
    (r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED_AWS_KEY]"),
    (r"\b(?:sk|ghp|xox[bp])[-_][A-Za-z0-9_-]{16,}\b", "[REDACTED_TOKEN]"),
    (r"\b(?:\d[ -]?){13,16}\b", "[REDACTED_NUMBER]"),
    (r"(?i)(password|passwd|pwd)\s*(is|=|:)\s*\S+", r"\1 \2 [REDACTED]"),
]


def is_injection(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in INJECTION_PATTERNS)


def redact(text: str) -> str:
    for pattern, repl in SECRET_PATTERNS:
        text = re.sub(pattern, repl, text)
    return text
