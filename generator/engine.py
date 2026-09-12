"""
Core generation engine.

Wraps the rule engine's candidate stream with:
  - optional streaming deduplication (memory-bounded via a seen-set of
    hashes when the candidate space is large)
  - a requested-count cutoff that stops as soon as enough unique
    candidates have been produced
  - accounting for statistics (generated, duplicates, requested vs possible,
    and a per-source-word breakdown)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from rules.definitions import RuleSet
from rules.engine import stream_candidates, stream_candidates_with_source


@dataclass
class GenerationStats:
    requested: int
    generated: int = 0
    duplicates: int = 0
    input_words: int = 0
    rules_enabled: int = 0
    per_word_counts: dict = field(default_factory=dict)

    @property
    def possible(self) -> int:
        """Total unique candidates seen (generated + duplicates encountered)."""
        return self.generated + self.duplicates


def deduplicating_stream(
    words: list[str],
    rules: RuleSet,
    limit: int | None = None,
    stats: GenerationStats | None = None,
    skip: int = 0,
) -> Iterator[str]:
    """
    Yield unique candidates from the rule engine, stopping at `limit`
    unique results if provided. Updates `stats` in place if given,
    including a per-source-word breakdown of how many candidates each
    seed word (or "combine") contributed.

    `skip` discards the first `skip` unique candidates without yielding
    them (but still counts them into `seen` for dedup purposes) -- this
    is what --resume uses to pick a deterministic run back up where a
    previous, interrupted run left off, without duplicating anything
    already written to the output file.

    Deduplication uses a set of the (short) candidate strings themselves,
    or of their lowercased form when rules.dedupe_case_insensitive is set
    (so e.g. "Yash1" and "YASH1" count as the same candidate).
    For extremely large runs this is the standard tradeoff for exact
    dedup; candidates are typically short strings so memory overhead
    per entry is modest.
    """
    seen: set[str] = set()
    count = 0
    skipped = 0

    for candidate, source in stream_candidates_with_source(words, rules):
        if rules.deduplicate:
            key = candidate.lower() if rules.dedupe_case_insensitive else candidate
            if key in seen:
                if stats:
                    stats.duplicates += 1
                continue
            seen.add(key)

        if skipped < skip:
            skipped += 1
            continue

        count += 1
        if stats:
            stats.generated = count
            stats.per_word_counts[source] = stats.per_word_counts.get(source, 0) + 1
        yield candidate
        if limit is not None and count >= limit:
            return


def count_full_space(words: list[str], rules: RuleSet) -> int:
    """
    Compute the exact size of the unique candidate space by fully
    streaming without a limit. Used for the 'Possible' statistic when
    the requested count exceeds what can be produced, and for --dry-run
    style exact planning on smaller word sets.
    """
    seen: set[str] = set()
    for candidate in stream_candidates(words, rules):
        if rules.deduplicate:
            key = candidate.lower() if rules.dedupe_case_insensitive else candidate
            seen.add(key)
        else:
            seen.add(id(candidate))  # never collides; just counts total
    return len(seen)
