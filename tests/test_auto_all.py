"""
Unit tests for --all and the "auto-all by default" behavior:
when the user gives no explicit rule flags, WL Gen should enable every
rule category automatically, scaled to comfortably cover the requested
count. Any explicit rule flag (or a config file) should disable this
default and use exactly what the user specified.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cli.flags import build_parser
from cli.resolve import resolve_ruleset, _user_picked_explicit_rules, _auto_all_ruleset
from config.loader import AppConfig
from generator.engine import deduplicating_stream, GenerationStats


class TestAutoAllDefault(unittest.TestCase):
    def setUp(self):
        self.parser = build_parser()

    def test_no_flags_triggers_all_categories(self):
        args = self.parser.parse(["-g", "-wd", "Rahul"])
        rs = resolve_ruleset(args, config=None, word_count=1, requested=1000)
        cats = rs.enabled_categories()
        self.assertIn("case", cats)
        self.assertIn("numbers", cats)
        self.assertIn("symbols", cats)
        self.assertIn("substitutions", cats)
        self.assertGreater(len(rs.case_modes), 1)

    def test_explicit_all_flag_same_as_no_flags(self):
        args_none = self.parser.parse(["-g", "-wd", "Rahul"])
        args_all = self.parser.parse(["-g", "-wd", "Rahul", "--all"])
        rs_none = resolve_ruleset(args_none, config=None, word_count=1, requested=1000)
        rs_all = resolve_ruleset(args_all, config=None, word_count=1, requested=1000)
        self.assertEqual(rs_none.enabled_categories(), rs_all.enabled_categories())
        self.assertEqual(rs_none.case_modes, rs_all.case_modes)
        self.assertEqual(rs_none.numbers, rs_all.numbers)
        self.assertEqual(rs_none.symbols, rs_all.symbols)

    def test_explicit_case_flag_narrows_only_case(self):
        # Picking one rule flag should narrow *that* category only --
        # other, unmentioned categories keep their sane defaults instead
        # of silently going empty/off.
        args = self.parser.parse(["-g", "-wd", "Rahul", "-c", "lower"])
        rs = resolve_ruleset(args, config=None, word_count=1, requested=1000)
        self.assertEqual(rs.case_modes, ["lower"])
        self.assertTrue(rs.numbers)
        self.assertTrue(rs.symbols)
        self.assertFalse(rs.use_substitutions)

    def test_explicit_numbers_flag_narrows_only_numbers(self):
        args = self.parser.parse(["-g", "-wd", "Rahul", "-N", "1,2,3"])
        rs = resolve_ruleset(args, config=None, word_count=1, requested=1000)
        self.assertEqual(rs.numbers, ["1", "2", "3"])
        self.assertTrue(rs.symbols)
        self.assertFalse(rs.use_substitutions)

    def test_explicit_leet_flag_narrows_only_substitutions(self):
        args = self.parser.parse(["-g", "-wd", "Rahul", "--leet"])
        rs = resolve_ruleset(args, config=None, word_count=1, requested=1000)
        self.assertTrue(rs.use_substitutions)
        self.assertTrue(rs.numbers)
        self.assertEqual(len(rs.case_modes), 1)  # only the default lower

    def test_config_file_disables_auto_all(self):
        config = AppConfig(raw={
            "generation": {"case": ["lower"], "numbers": ["1"]},
            "output": {"deduplicate": True},
        })
        args = self.parser.parse(["-g", "-wd", "Rahul", "--config", "dummy.toml"])
        rs = resolve_ruleset(args, config=config, word_count=1, requested=1000)
        self.assertEqual(rs.case_modes, ["lower"])
        self.assertEqual(rs.numbers, ["1"])
        self.assertEqual(rs.symbols, [])

    def test_single_explicit_flag_still_produces_mixed_output(self):
        # Regression test: previously, giving any single rule flag (e.g.
        # just -c) reset every other category to empty, so a run like
        # `-g -wd Rahul -c lower,upper` produced only case variants with
        # no numbers/symbols mixed in at all, instead of layering the
        # chosen category on top of sane defaults for the rest.
        args = self.parser.parse(["-g", "-wd", "Rahul", "-c", "lower,upper"])
        rs = resolve_ruleset(args, config=None, word_count=1, requested=2000)
        stats = GenerationStats(requested=2000)
        results = list(deduplicating_stream(["rahul"], rs, limit=2000, stats=stats))

        has_digit_suffix = any(r[-1].isdigit() for r in results if r)
        has_symbol = any(any(ch in "!@#$*_." for ch in r) for r in results)
        self.assertTrue(has_digit_suffix, "expected numeric suffixes even though only -c was given")
        self.assertTrue(has_symbol, "expected symbol suffixes even though only -c was given")

    def test_helper_detects_explicit_rule_flags(self):
        args_plain = self.parser.parse(["-g", "-wd", "Rahul"])
        args_with_case = self.parser.parse(["-g", "-wd", "Rahul", "-c", "upper"])
        self.assertFalse(_user_picked_explicit_rules(args_plain))
        self.assertTrue(_user_picked_explicit_rules(args_with_case))


class TestAutoAllScaling(unittest.TestCase):
    def test_small_request_uses_small_number_range(self):
        rs = _auto_all_ruleset(word_count=1, requested=500)
        self.assertEqual(len(rs.numbers), 100)  # 0..99

    def test_medium_request_widens_number_range(self):
        rs = _auto_all_ruleset(word_count=1, requested=50_000)
        self.assertEqual(len(rs.numbers), 10_000)  # 0..9999

    def test_large_request_widens_further(self):
        rs = _auto_all_ruleset(word_count=1, requested=2_000_000)
        self.assertEqual(len(rs.numbers), 100_000)  # 0..99999

    def test_very_large_request_widens_maximally(self):
        rs = _auto_all_ruleset(word_count=1, requested=8_000_000)
        self.assertEqual(len(rs.numbers), 1_000_000)  # 0..999999

    def test_combine_enabled_for_multi_word_large_requests(self):
        rs_small = _auto_all_ruleset(word_count=2, requested=5_000)
        rs_large = _auto_all_ruleset(word_count=2, requested=50_000)
        self.assertFalse(rs_small.combine_words)
        self.assertTrue(rs_large.combine_words)

    def test_combine_disabled_for_single_word(self):
        rs = _auto_all_ruleset(word_count=1, requested=10_000_000)
        self.assertFalse(rs.combine_words)


class TestAutoAllIntegration(unittest.TestCase):
    """End-to-end: the auto-all ruleset should actually satisfy the
    exact scenario the user described -- give a word and a count, get
    that many real, deduplicated, mixed-rule candidates back."""

    def setUp(self):
        self.parser = build_parser()

    def test_reaches_requested_count_with_no_flags(self):
        args = self.parser.parse(["-g", "-wd", "Rahul", "-n", "5000"])
        rs = resolve_ruleset(args, config=None, word_count=1, requested=5000)
        stats = GenerationStats(requested=5000)
        results = list(deduplicating_stream(["rahul"], rs, limit=5000, stats=stats))
        self.assertEqual(len(results), 5000)
        self.assertEqual(stats.duplicates + stats.generated >= 5000, True)
        self.assertEqual(len(results), len(set(results)))

    def test_output_is_actually_mixed_not_single_flavor(self):
        """Guards against a regression where 'auto-all' silently degrades
        to only one rule category (e.g. only numbers, or only case)."""
        args = self.parser.parse(["-g", "-wd", "Rahul", "-n", "2000"])
        rs = resolve_ruleset(args, config=None, word_count=1, requested=2000)
        stats = GenerationStats(requested=2000)
        results = list(deduplicating_stream(["rahul"], rs, limit=2000, stats=stats))

        has_upper = any(r.isupper() for r in results)
        has_digit_suffix = any(r[-1].isdigit() for r in results if r)
        has_symbol = any(any(ch in "!@#$*_." for ch in r) for r in results)

        self.assertTrue(has_upper, "expected at least one all-uppercase variant")
        self.assertTrue(has_digit_suffix, "expected at least one numeric-suffixed variant")
        self.assertTrue(has_symbol, "expected at least one symbol-suffixed variant")


if __name__ == "__main__":
    unittest.main()
