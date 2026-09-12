"""Unit tests for the custom CLI argument parser."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cli.flags import build_parser
from utils.errors import ArgumentError


class TestArgParser(unittest.TestCase):
    def setUp(self):
        self.parser = build_parser()

    def test_simple_flag(self):
        args = self.parser.parse(["-g"])
        self.assertTrue(args.get("generate"))

    def test_value_flag(self):
        args = self.parser.parse(["-o", "out.txt"])
        self.assertEqual(args.get("output"), "out.txt")

    def test_repeated_flag_accumulates(self):
        args = self.parser.parse(["-wd", "Rahul", "-wd", "Kumar"])
        self.assertEqual(args.get("word"), ["Rahul", "Kumar"])

    def test_combined_flags(self):
        args = self.parser.parse(["-g", "-wd", "Rahul", "-n", "10000", "-o", "result.txt"])
        self.assertTrue(args.get("generate"))
        self.assertEqual(args.get("word"), ["Rahul"])
        self.assertEqual(args.get("count"), "10000")
        self.assertEqual(args.get("output"), "result.txt")

    def test_unrecognized_flag_raises(self):
        with self.assertRaises(ArgumentError):
            self.parser.parse(["--totally-not-real"])

    def test_missing_value_raises(self):
        with self.assertRaises(ArgumentError):
            self.parser.parse(["-o"])

    def test_inline_equals_syntax(self):
        args = self.parser.parse(["--output=out.txt"])
        self.assertEqual(args.get("output"), "out.txt")

    def test_flag_with_inline_value_raises(self):
        with self.assertRaises(ArgumentError):
            self.parser.parse(["-g=true"])

    def test_defaults_are_sane(self):
        args = self.parser.parse([])
        self.assertFalse(args.get("generate"))
        self.assertEqual(args.get("word"), [])
        self.assertIsNone(args.get("output"))

    def test_short_and_long_form_equivalent(self):
        a1 = self.parser.parse(["-g"])
        a2 = self.parser.parse(["--generate"])
        self.assertEqual(a1.get("generate"), a2.get("generate"))


if __name__ == "__main__":
    unittest.main()
