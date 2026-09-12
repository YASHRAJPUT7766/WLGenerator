"""Unit tests for range-expansion syntax in -N/--numbers (range:START-END)."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cli.resolve import _expand_range_token, _split_csv_with_ranges, resolve_ruleset
from cli.flags import build_parser
from utils.errors import ArgumentError
from generator.engine import deduplicating_stream, GenerationStats


class TestRangeExpansion(unittest.TestCase):
    def test_basic_range(self):
        result = _expand_range_token("range:0-9", "-N")
        self.assertEqual(result, [str(i) for i in range(10)])

    def test_range_inclusive_of_end(self):
        result = _expand_range_token("range:5-8", "-N")
        self.assertEqual(result, ["5", "6", "7", "8"])

    def test_range_with_step(self):
        result = _expand_range_token("range:0-20:5", "-N")
        self.assertEqual(result, ["0", "5", "10", "15", "20"])

    def test_zero_padding(self):
        result = _expand_range_token("range:0-99", "-N", zero_pad=True)
        self.assertEqual(result[0], "00")
        self.assertEqual(result[1], "01")
        self.assertEqual(result[-1], "99")

    def test_no_padding_by_default(self):
        result = _expand_range_token("range:0-99", "-N", zero_pad=False)
        self.assertEqual(result[0], "0")
        self.assertEqual(result[-1], "99")

    def test_start_greater_than_end_raises(self):
        with self.assertRaises(ArgumentError):
            _expand_range_token("range:10-5", "-N")

    def test_non_numeric_bounds_raise(self):
        with self.assertRaises(ArgumentError):
            _expand_range_token("range:abc-99", "-N")

    def test_missing_dash_raises(self):
        with self.assertRaises(ArgumentError):
            _expand_range_token("range:100", "-N")

    def test_zero_or_negative_step_raises(self):
        with self.assertRaises(ArgumentError):
            _expand_range_token("range:0-10:0", "-N")

    def test_oversized_range_raises(self):
        with self.assertRaises(ArgumentError):
            _expand_range_token("range:0-99999999", "-N")

    def test_mixed_plain_values_and_range(self):
        result = _split_csv_with_ranges("1,12,range:2000-2002", "-N")
        self.assertEqual(result, ["1", "12", "2000", "2001", "2002"])

    def test_multiple_ranges(self):
        result = _split_csv_with_ranges("range:0-2,range:10-12", "-N")
        self.assertEqual(result, ["0", "1", "2", "10", "11", "12"])

    def test_plain_csv_without_range_unaffected(self):
        result = _split_csv_with_ranges("1,12,123", "-N")
        self.assertEqual(result, ["1", "12", "123"])

    def test_empty_value_returns_empty(self):
        self.assertEqual(_split_csv_with_ranges(None, "-N"), [])
        self.assertEqual(_split_csv_with_ranges("", "-N"), [])


class TestRangeIntegrationWithCLI(unittest.TestCase):
    """End-to-end: -N range:... flows through argument resolution and
    into the actual generation engine, matching a real invocation."""

    def setUp(self):
        self.parser = build_parser()

    def test_range_flows_into_ruleset(self):
        args = self.parser.parse(["-g", "-wd", "Rahul", "-N", "range:0-9"])
        rs = resolve_ruleset(args, config=None)
        self.assertEqual(rs.numbers, [str(i) for i in range(10)])

    def test_range_reaches_full_requested_count(self):
        """
        Reproduces the exact user scenario: give one word, ask for a
        specific count, and the numeric range alone should be enough to
        satisfy it without manually listing every number.
        """
        args = self.parser.parse(["-g", "-wd", "Rahul", "-N", "range:0-9999"])
        rs = resolve_ruleset(args, config=None)
        stats = GenerationStats(requested=10000)
        results = list(deduplicating_stream(["rahul"], rs, limit=10000, stats=stats))
        self.assertEqual(len(results), 10000)
        self.assertEqual(stats.generated, 10000)
        self.assertEqual(stats.duplicates, 0)
        self.assertIn("rahul", results)
        # The base word ("rahul") itself is candidate #1, so with a
        # requested count of exactly 10,000 the range only needs to
        # supply 9,999 more (rahul0 .. rahul9998) before the limit is
        # reached -- rahul9999 is simply never asked for. Confirm the
        # range keeps supplying fresh numbers right up to the cutoff.
        self.assertIn("rahul9998", results)

    def test_pad_flag_applies_zero_padding(self):
        args = self.parser.parse(["-g", "-wd", "Rahul", "-N", "range:0-99", "--pad"])
        rs = resolve_ruleset(args, config=None)
        self.assertIn("00", rs.numbers)
        self.assertIn("99", rs.numbers)
        self.assertNotIn("0", rs.numbers)  # should be padded, not bare


if __name__ == "__main__":
    unittest.main()
