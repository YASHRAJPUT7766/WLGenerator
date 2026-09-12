"""
Rule definitions for the deterministic transformation engine.

Each rule category is a pure function: (word: str) -> list[str], producing
one or more variants of the input word. The engine composes enabled
categories together (case, prefix, suffix, numbers, symbols, separators,
leet substitutions) to build the full candidate space.

Rules are intentionally simple, transparent, and local — this module
performs no network access and does not attempt any credential testing.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_NUMBERS = ["1", "12", "123", "2024", "2025", "01", "007", "99"]
DEFAULT_SYMBOLS = ["!", "@", "#", "$", "*", "_", "."]
DEFAULT_PREFIXES: list[str] = []
DEFAULT_SUFFIXES: list[str] = []
DEFAULT_SEPARATORS = [""]

# Common, conservative leetspeak-style substitutions used for defensive
# password-strength coverage (e.g. auditing whether "P@ssw0rd"-style
# variants of a known word appear in a breach corpus).
LEET_MAP = {
    "a": ["a", "@", "4"],
    "e": ["e", "3"],
    "i": ["i", "1", "!"],
    "o": ["o", "0"],
    "s": ["s", "$", "5"],
    "t": ["t", "7"],
}


@dataclass
class RuleSet:
    """The full set of enabled transformation rules for a generation run."""
    case_modes: list[str] = field(default_factory=lambda: ["lower"])
    prefixes: list[str] = field(default_factory=lambda: list(DEFAULT_PREFIXES))
    suffixes: list[str] = field(default_factory=lambda: list(DEFAULT_SUFFIXES))
    numbers: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    separators: list[str] = field(default_factory=lambda: list(DEFAULT_SEPARATORS))
    use_substitutions: bool = False
    combine_words: bool = False
    min_length: int | None = None
    max_length: int | None = None
    deduplicate: bool = True
    dedupe_case_insensitive: bool = False

    def enabled_categories(self) -> list[str]:
        cats = []
        if self.case_modes:
            cats.append("case")
        if self.prefixes:
            cats.append("prefix")
        if self.suffixes:
            cats.append("suffix")
        if self.numbers:
            cats.append("numbers")
        if self.symbols:
            cats.append("symbols")
        if self.use_substitutions:
            cats.append("substitutions")
        if self.combine_words:
            cats.append("combinations")
        if self.deduplicate:
            cats.append("deduplicate")
        return cats

    def rule_count(self) -> int:
        """A rough 'rules enabled' count for display purposes."""
        return len(self.enabled_categories())


# --- Individual transformation functions -----------------------------------

def apply_case(word: str, modes: list[str]) -> list[str]:
    out = []
    for mode in modes:
        if mode == "lower":
            out.append(word.lower())
        elif mode == "upper":
            out.append(word.upper())
        elif mode == "capitalize":
            out.append(word.capitalize())
        elif mode == "title":
            out.append(word.title())
        else:
            out.append(word)
    return out


def apply_substitutions(word: str) -> list[str]:
    """
    Generate leetspeak-style substitution variants.
    Limited to a single substitution combination pass to keep the space
    bounded and deterministic; not a full cartesian explosion.
    """
    variants = {word}
    lowered = word.lower()
    # Single-character substitution variants (each character independently)
    for i, ch in enumerate(lowered):
        options = LEET_MAP.get(ch)
        if not options:
            continue
        for opt in options[1:]:
            variant = lowered[:i] + opt + lowered[i + 1:]
            variants.add(variant)
    return list(variants)


def apply_affixes(words: list[str], prefixes: list[str], suffixes: list[str],
                   separators: list[str]) -> list[str]:
    if not prefixes and not suffixes:
        return words
    seps = separators or [""]
    out = []
    pre_list = prefixes or [""]
    suf_list = suffixes or [""]
    for w in words:
        for pre in pre_list:
            for suf in suf_list:
                for sep in seps:
                    parts = []
                    if pre:
                        parts.append(pre)
                    parts.append(w)
                    if suf:
                        parts.append(suf)
                    out.append(sep.join(parts) if (pre or suf) else w)
    return out


def apply_numbers(words: list[str], numbers: list[str]) -> list[str]:
    if not numbers:
        return words
    out = list(words)
    for w in words:
        for num in numbers:
            out.append(f"{w}{num}")
    return out


def apply_symbols(words: list[str], symbols: list[str]) -> list[str]:
    if not symbols:
        return words
    out = list(words)
    for w in words:
        for sym in symbols:
            out.append(f"{w}{sym}")
    return out


def apply_length_filter(words: list[str], min_len: int | None,
                         max_len: int | None) -> list[str]:
    if min_len is None and max_len is None:
        return words
    out = []
    for w in words:
        if min_len is not None and len(w) < min_len:
            continue
        if max_len is not None and len(w) > max_len:
            continue
        out.append(w)
    return out
