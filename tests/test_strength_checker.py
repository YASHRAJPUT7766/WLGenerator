"""Unit tests for local password strength analysis."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from checker.strength import analyze_password


class TestPasswordStrength(unittest.TestCase):
    def test_common_password_is_very_weak(self):
        report = analyze_password("password")
        self.assertEqual(report.verdict, "Very Weak")
        self.assertTrue(report.common_password_match)

    def test_dictionary_plus_digits_is_very_weak(self):
        report = analyze_password("password123")
        self.assertEqual(report.verdict, "Very Weak")
        self.assertTrue(any("weak base word" in n for n in report.predictable_pattern_notes))

    def test_long_random_password_is_strong(self):
        report = analyze_password("Xk9$mQ2!vLp8")
        self.assertIn(report.verdict, ("Strong", "Very Strong"))

    def test_diceware_style_is_very_strong(self):
        report = analyze_password("correcthorsebatterystaple")
        self.assertEqual(report.verdict, "Very Strong")

    def test_repetition_detected(self):
        report = analyze_password("aaabbbccc111")
        self.assertTrue(report.repetition_detected)

    def test_sequential_detected(self):
        report = analyze_password("abcdef123456")
        self.assertTrue(report.sequential_detected)

    def test_diversity_score(self):
        report = analyze_password("Ab1!")
        self.assertEqual(report.diversity_score, 4)

    def test_never_raises_on_empty_password(self):
        report = analyze_password("")
        self.assertEqual(report.password_length, 0)

    def test_never_raises_on_unicode(self):
        report = analyze_password("pässwörd123ü")
        self.assertGreaterEqual(report.password_length, 1)


if __name__ == "__main__":
    unittest.main()
