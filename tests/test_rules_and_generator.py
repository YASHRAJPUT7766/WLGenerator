"""Unit tests for rule definitions and the generation engine."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rules.definitions import RuleSet, apply_case, apply_numbers, apply_symbols
from rules.engine import build_variant_pool, stream_candidates, estimate_candidate_space
from generator.engine import deduplicating_stream, GenerationStats, count_full_space


class TestCaseTransform(unittest.TestCase):
    def test_lower(self):
        self.assertEqual(apply_case("Rahul", ["lower"]), ["rahul"])

    def test_upper(self):
        self.assertEqual(apply_case("Rahul", ["upper"]), ["RAHUL"])

    def test_multiple_modes(self):
        result = apply_case("rahul", ["lower", "upper", "capitalize"])
        self.assertEqual(result, ["rahul", "RAHUL", "Rahul"])


class TestNumberSymbolTransforms(unittest.TestCase):
    def test_numbers_appends_and_keeps_base(self):
        result = apply_numbers(["rahul"], ["1", "2"])
        self.assertEqual(result, ["rahul", "rahul1", "rahul2"])

    def test_symbols_appends_and_keeps_base(self):
        result = apply_symbols(["rahul"], ["!", "@"])
        self.assertEqual(result, ["rahul", "rahul!", "rahul@"])

    def test_no_numbers_passthrough(self):
        result = apply_numbers(["rahul"], [])
        self.assertEqual(result, ["rahul"])


class TestVariantPool(unittest.TestCase):
    def test_simple_pool_size(self):
        rs = RuleSet(case_modes=["lower", "upper"], numbers=["1"], symbols=[])
        variants = build_variant_pool("rahul", rs)
        # case(2) -> numbers adds +1 variant per input = 2 + 2 = 4
        self.assertEqual(len(variants), 4)
        self.assertIn("rahul", variants)
        self.assertIn("RAHUL", variants)
        self.assertIn("rahul1", variants)
        self.assertIn("RAHUL1", variants)

    def test_no_duplicates_in_deterministic_stream(self):
        rs = RuleSet(case_modes=["lower", "upper", "capitalize"],
                     numbers=["1", "2", "3"], symbols=["!", "@"])
        candidates = list(stream_candidates(["rahul"], rs))
        deduped = list(dict.fromkeys(candidates))
        # The raw stream itself may contain no accidental collisions for
        # this rule combination; verify by comparing against a set.
        self.assertEqual(len(candidates), len(set(candidates)))


class TestDeduplicatingStream(unittest.TestCase):
    def test_respects_limit(self):
        rs = RuleSet(case_modes=["lower", "upper"], numbers=[str(i) for i in range(50)])
        stats = GenerationStats(requested=5)
        result = list(deduplicating_stream(["rahul"], rs, limit=5, stats=stats))
        self.assertEqual(len(result), 5)
        self.assertEqual(stats.generated, 5)

    def test_no_duplicate_entries_written(self):
        rs = RuleSet(case_modes=["lower"], numbers=["1"], symbols=["!"])
        stats = GenerationStats(requested=100)
        result = list(deduplicating_stream(["rahul"], rs, limit=100, stats=stats))
        self.assertEqual(len(result), len(set(result)))

    def test_stops_when_space_exhausted(self):
        # Single word, lowercase only, no other rules -> exactly 1 possible candidate
        rs = RuleSet(case_modes=["lower"])
        stats = GenerationStats(requested=1000)
        result = list(deduplicating_stream(["rahul"], rs, limit=1000, stats=stats))
        self.assertEqual(len(result), 1)
        self.assertEqual(stats.generated, 1)
        self.assertEqual(result[0], "rahul")

    def test_full_space_count_matches_generation(self):
        rs = RuleSet(case_modes=["lower", "upper"], numbers=["1", "2"], symbols=["!"])
        full = count_full_space(["rahul"], rs)
        stats = GenerationStats(requested=full)
        generated = list(deduplicating_stream(["rahul"], rs, limit=full, stats=stats))
        self.assertEqual(len(generated), full)


class TestMultiWordAndCombine(unittest.TestCase):
    def test_combine_produces_pairwise_concatenations(self):
        rs = RuleSet(case_modes=["lower"], combine_words=True)
        candidates = list(stream_candidates(["rahul", "kumar"], rs))
        self.assertIn("rahulkumar", candidates)
        self.assertIn("kumarrahul", candidates)

    def test_no_combine_flag_skips_combinations(self):
        rs = RuleSet(case_modes=["lower"], combine_words=False)
        candidates = list(stream_candidates(["rahul", "kumar"], rs))
        self.assertNotIn("rahulkumar", candidates)

    def test_multiple_words_share_output_evenly_when_limited(self):
        # Regression test: previously, words were exhausted sequentially,
        # so if the first word's variant pool alone exceeded the
        # requested count, a limited/streamed run would fill up entirely
        # from that one word and later words would never appear at all.
        words = ["rahul", "kumar", "sharma", "singh", "verma"]
        rs = RuleSet(
            case_modes=["lower", "upper", "capitalize", "title"],
            numbers=[str(n) for n in range(100)],
            symbols=["!", "@", "#", "$", "*", "_", "."],
            use_substitutions=True,
        )
        stats = GenerationStats(requested=1000)
        results = list(deduplicating_stream(words, rs, limit=1000, stats=stats))
        self.assertEqual(len(results), 1000)

        pools = {w: set(build_variant_pool(w, rs)) for w in words}
        counts = {w: 0 for w in words}
        for r in results:
            for w in words:
                if r in pools[w]:
                    counts[w] += 1
                    break

        for w in words:
            self.assertGreater(counts[w], 0, f"expected at least some candidates from '{w}'")
        # Each word's pool is comparable in size, so with round-robin
        # interleaving every word should land close to an even 1000/5 share.
        for w in words:
            self.assertGreater(counts[w], 100, f"'{w}' got far fewer than its fair share: {counts}")


class TestLengthFilter(unittest.TestCase):
    def test_min_max_length_filters_variants(self):
        rs = RuleSet(case_modes=["lower"], numbers=["1", "12", "123"], min_length=7, max_length=8)
        variants = build_variant_pool("rahul", rs)
        for v in variants:
            self.assertGreaterEqual(len(v), 7)
            self.assertLessEqual(len(v), 8)


if __name__ == "__main__":
    unittest.main()
