"""
Random mode: a controlled random test-data generator, independent from
the deterministic rule-based word engine.

This mode produces random strings from a configurable character set and
length — useful for generating filler/control datasets in local testing
(e.g. benchmark noise, control groups) rather than mutating real words.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Iterator

CHARSET_PRESETS = {
    "alnum": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "alpha": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "lower": "abcdefghijklmnopqrstuvwxyz",
    "upper": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "digits": "0123456789",
    "full": (
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789!@#$%^&*()-_=+"
    ),
}


@dataclass
class RandomModeConfig:
    length: int = 12
    count: int = 1000
    charset: str = "alnum"
    deduplicate: bool = True

    def resolved_charset(self) -> str:
        if self.charset in CHARSET_PRESETS:
            return CHARSET_PRESETS[self.charset]
        # Treat as a literal custom character set string
        return self.charset


def stream_random_candidates(config: RandomModeConfig) -> Iterator[str]:
    """
    Yield cryptographically-random strings (via `secrets`) of the
    configured length, drawn from the configured character set.
    Uses secrets.choice for a non-predictable control-data generator.
    """
    alphabet = config.resolved_charset()
    if not alphabet:
        raise ValueError("Random mode character set is empty.")

    seen: set[str] = set()
    produced = 0
    # Safety cap on retry attempts to avoid an infinite loop if the
    # requested count exceeds the realistic unique space for short lengths.
    max_attempts = config.count * 50 + 10000
    attempts = 0

    while produced < config.count and attempts < max_attempts:
        attempts += 1
        candidate = "".join(secrets.choice(alphabet) for _ in range(config.length))
        if config.deduplicate:
            if candidate in seen:
                continue
            seen.add(candidate)
        produced += 1
        yield candidate
