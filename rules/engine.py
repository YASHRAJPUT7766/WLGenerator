"""
Rule engine: composes enabled transformation categories into a single
streaming pipeline that yields candidate strings without holding the
entire output in memory.
"""
from __future__ import annotations

import itertools
from typing import Iterator

from rules.definitions import (
    RuleSet,
    apply_case,
    apply_substitutions,
    apply_affixes,
    apply_numbers,
    apply_symbols,
    apply_length_filter,
)


def _combine_seed_words(words: list[str], max_pairs: int = 2000) -> list[str]:
    """
    Produce simple pairwise concatenations of seed words
    (e.g. ["yash", "kumar"] -> "yashkumar", "kumaryash").
    Bounded to avoid combinatorial blowup on large wordlists.
    """
    if len(words) < 2:
        return []
    combos = []
    pairs = itertools.permutations(words, 2)
    for i, (a, b) in enumerate(pairs):
        if i >= max_pairs:
            break
        combos.append(f"{a}{b}")
    return combos


def build_variant_pool(word: str, rules: RuleSet) -> list[str]:
    """
    Build the full set of variants for a single seed word under the
    given rule set. This is used for preview/estimation; the streaming
    generator below re-derives variants lazily per word to stay memory
    efficient for very large runs.
    """
    variants = apply_case(word, rules.case_modes or ["lower"])

    if rules.use_substitutions:
        expanded = []
        for v in variants:
            expanded.extend(apply_substitutions(v))
        variants = expanded

    variants = apply_affixes(variants, rules.prefixes, rules.suffixes, rules.separators)
    variants = apply_numbers(variants, rules.numbers)
    variants = apply_symbols(variants, rules.symbols)
    variants = apply_length_filter(variants, rules.min_length, rules.max_length)

    return variants


def estimate_candidate_space(words: list[str], rules: RuleSet) -> int:
    """
    Estimate the total number of unique candidates possible under the
    rule set, without materializing the full set (uses sampling for
    large word lists to stay fast).
    """
    sample_size = min(len(words), 25)
    sample = words[:sample_size]

    total = 0
    seen_sample_variants = set()
    for w in sample:
        variants = build_variant_pool(w, rules)
        seen_sample_variants.update(variants)

    if rules.combine_words and len(words) >= 2:
        combo_sample = _combine_seed_words(sample)
        seen_sample_variants.update(combo_sample)

    if sample_size == len(words):
        return len(seen_sample_variants)

    # Extrapolate proportionally for large word sources; this is a
    # heuristic estimate, refined to the true value once generation runs
    # with actual deduplication.
    avg_variants_per_word = len(seen_sample_variants) / max(sample_size, 1)
    total = int(avg_variants_per_word * len(words))
    return max(total, len(seen_sample_variants))


def stream_candidates(words: list[str], rules: RuleSet) -> Iterator[str]:
    """
    Lazily yield candidate strings for the given seed words and rule set.
    Deduplication (if enabled) is handled by the caller using a
    memory-bounded strategy (see generator.engine.deduplicating_stream).

    Words are interleaved round-robin (one variant from each word in
    turn) rather than fully exhausting one word before moving to the
    next. With multiple source words, a single word's variant pool can
    easily exceed the requested count on its own -- if words were
    processed sequentially, a limited/streamed consumer (see
    generator.engine.deduplicating_stream) could hit its limit and stop
    while still on the first word, so later words would never
    contribute anything to the output. Interleaving means every word
    gets a fair, evenly-distributed share of the output regardless of
    where the requested count cuts the stream off.
    """
    for candidate, _source in stream_candidates_with_source(words, rules):
        yield candidate


def stream_candidates_with_source(words: list[str], rules: RuleSet) -> Iterator[tuple[str, str]]:
    """
    Like stream_candidates, but yields (candidate, source_word) pairs so
    callers can attribute each candidate back to the seed word (or
    "combine" for pairwise word-combination candidates) it came from --
    used for the per-source breakdown in --stats.
    """
    pools = [(word, build_variant_pool(word, rules)) for word in words]
    iterators = [(word, iter(pool)) for word, pool in pools]
    active = list(iterators)
    while active:
        next_active = []
        for word, it in active:
            try:
                candidate = next(it)
            except StopIteration:
                continue
            yield candidate, word
            next_active.append((word, it))
        active = next_active

    if rules.combine_words and len(words) >= 2:
        for combo in _combine_seed_words(words):
            for variant in build_variant_pool(combo, rules):
                yield variant, "combine"
