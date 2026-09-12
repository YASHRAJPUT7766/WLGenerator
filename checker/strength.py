"""
Local password strength analysis.

Purely local, offline analysis of a single password's structural
properties. Nothing is transmitted, logged externally, or stored.
This is a defensive/educational heuristic estimator, not a
cryptographic guarantee, and it is not connected to any live
authentication system.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

COMMON_WEAK_PASSWORDS = {
    "password", "123456", "12345678", "qwerty", "abc123", "letmein",
    "monkey", "111111", "iloveyou", "admin", "welcome", "password1",
    "123456789", "football", "dragon", "master", "sunshine", "princess",
}

# Common dictionary-ish bases that, combined with a trailing digit run,
# constitute a well-known weak construction (e.g. "password123",
# "admin2024"). This is a small illustrative list for pattern detection,
# not an attempt at a full dictionary attack.
COMMON_WEAK_BASES = {
    "password", "qwerty", "letmein", "welcome", "admin", "monkey",
    "dragon", "master", "sunshine", "princess", "football", "iloveyou",
    "abc", "test", "user", "login", "guest", "changeme",
}

SEQUENTIAL_RUNS = [
    "abcdefghijklmnopqrstuvwxyz",
    "0123456789",
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm",
]


@dataclass
class StrengthReport:
    password_length: int
    charset_size: int
    entropy_bits: float
    diversity_score: int
    has_lower: bool
    has_upper: bool
    has_digit: bool
    has_symbol: bool
    repetition_detected: bool
    sequential_detected: bool
    common_password_match: bool
    predictable_pattern_notes: list[str] = field(default_factory=list)
    verdict: str = ""
    estimated_crack_time: str = ""


def _charset_size(password: str) -> int:
    size = 0
    if re.search(r"[a-z]", password):
        size += 26
    if re.search(r"[A-Z]", password):
        size += 26
    if re.search(r"[0-9]", password):
        size += 10
    if re.search(r"[^a-zA-Z0-9]", password):
        size += 33
    return size or 1


def _has_repetition(password: str) -> bool:
    # 3+ identical characters in a row, or a repeated block (e.g. "abab", "abcabc")
    if re.search(r"(.)\1{2,}", password):
        return True
    for block_len in (2, 3, 4):
        for i in range(len(password) - block_len * 2 + 1):
            block = password[i:i + block_len]
            if password[i + block_len:i + 2 * block_len] == block:
                return True
    return False


def _has_sequential(password: str) -> bool:
    lowered = password.lower()
    for run in SEQUENTIAL_RUNS:
        for i in range(len(run) - 2):
            forward = run[i:i + 3]
            backward = forward[::-1]
            if forward in lowered or backward in lowered:
                return True
    return False


def _predictable_notes(password: str) -> list[str]:
    notes = []
    if re.search(r"(19|20)\d{2}$", password):
        notes.append("Ends in a 4-digit year (commonly guessed pattern).")
    if re.search(r"^[A-Z][a-z]+\d{1,4}$", password):
        notes.append("Matches 'Capitalized word + short number' pattern.")
    if re.search(r"[!@#$*]$", password) and password[:-1].isalpha():
        notes.append("Single trailing symbol after a plain word.")

    match = re.match(r"^([a-zA-Z]+)(\d+)$", password)
    if match:
        base = match.group(1).lower()
        if base in COMMON_WEAK_BASES:
            notes.append(
                f"Matches a well-known weak base word ('{base}') followed by digits."
            )
    return notes


def _estimate_crack_time(entropy_bits: float) -> str:
    # Assumes a conservative offline guessing rate of 1e10 guesses/sec
    # for a fast hash — purely illustrative, not tied to any specific
    # attack scenario or system.
    guesses = 2 ** entropy_bits
    seconds = guesses / 1e10
    if seconds < 1:
        return "instant"
    if seconds < 60:
        return f"~{seconds:.1f} seconds"
    minutes = seconds / 60
    if minutes < 60:
        return f"~{minutes:.1f} minutes"
    hours = minutes / 60
    if hours < 24:
        return f"~{hours:.1f} hours"
    days = hours / 24
    if days < 365:
        return f"~{days:.1f} days"
    years = days / 365
    if years > 1e6:
        return "practically uncrackable (offline, current hardware)"
    return f"~{years:,.0f} years"


def analyze_password(password: str) -> StrengthReport:
    length = len(password)
    charset = _charset_size(password)
    entropy = length * math.log2(charset) if charset > 1 else 0.0

    has_lower = bool(re.search(r"[a-z]", password))
    has_upper = bool(re.search(r"[A-Z]", password))
    has_digit = bool(re.search(r"[0-9]", password))
    has_symbol = bool(re.search(r"[^a-zA-Z0-9]", password))
    diversity_score = sum([has_lower, has_upper, has_digit, has_symbol])

    repetition = _has_repetition(password)
    sequential = _has_sequential(password)
    common_match = password.lower() in COMMON_WEAK_PASSWORDS
    notes = _predictable_notes(password)
    weak_base_match = any("well-known weak base word" in n for n in notes)

    # Verdict heuristic. Raw character-set entropy overstates real-world
    # guessability for passwords built from a dictionary word plus a
    # predictable suffix, since attackers try those constructions before
    # brute force — so pattern matches are penalized heavily rather than
    # letting entropy alone decide the verdict.
    penalty = 0
    if repetition:
        penalty += 1
    if sequential:
        penalty += 1
    if common_match:
        penalty += 3
    if weak_base_match:
        penalty += 4
    elif notes:
        penalty += 1
    if length < 8:
        penalty += 2
    if diversity_score <= 2:
        penalty += 1

    score = entropy - (penalty * 8)
    if common_match or weak_base_match or score < 20:
        verdict = "Very Weak"
    elif score < 40:
        verdict = "Weak"
    elif score < 60:
        verdict = "Moderate"
    elif score < 80:
        verdict = "Strong"
    else:
        verdict = "Very Strong"

    return StrengthReport(
        password_length=length,
        charset_size=charset,
        entropy_bits=round(entropy, 1),
        diversity_score=diversity_score,
        has_lower=has_lower,
        has_upper=has_upper,
        has_digit=has_digit,
        has_symbol=has_symbol,
        repetition_detected=repetition,
        sequential_detected=sequential,
        common_password_match=common_match,
        predictable_pattern_notes=notes,
        verdict=verdict,
        estimated_crack_time=_estimate_crack_time(max(entropy - penalty * 8, 0)),
    )
