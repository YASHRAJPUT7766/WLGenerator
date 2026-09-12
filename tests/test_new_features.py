"""
Unit tests for features added after the initial release:
  - case-insensitive deduplication (--dedupe-ci)
  - per-source-word statistics breakdown (used by --stats)
  - alternate output formats: csv, jsonl (--format / inferred from extension)
  - sorted output (--sort)
  - resume support for interrupted runs (--resume)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rules.definitions import RuleSet
from generator.engine import deduplicating_stream, GenerationStats
from output.writer import (
    write_stream_to_file, infer_output_format, sort_candidates, VALID_OUTPUT_FORMATS,
)
from generator.resume import (
    save_resume_state, load_resume_state, clear_resume_state, resume_path_for,
)
from utils.errors import OutputError


class TestCaseInsensitiveDedupe(unittest.TestCase):
    def test_case_sensitive_dedupe_keeps_both_cases(self):
        rs = RuleSet(case_modes=["lower", "upper"], dedupe_case_insensitive=False)
        results = list(deduplicating_stream(["rahul"], rs, limit=100))
        self.assertIn("rahul", results)
        self.assertIn("RAHUL", results)

    def test_case_insensitive_dedupe_keeps_only_first(self):
        rs = RuleSet(case_modes=["lower", "upper"], dedupe_case_insensitive=True)
        results = list(deduplicating_stream(["rahul"], rs, limit=100))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].lower(), "rahul")


class TestPerWordStats(unittest.TestCase):
    def test_per_word_counts_track_source(self):
        words = ["rahul", "kumar"]
        rs = RuleSet(case_modes=["lower", "upper"], numbers=["1", "2", "3"])
        stats = GenerationStats(requested=1000)
        results = list(deduplicating_stream(words, rs, limit=1000, stats=stats))
        self.assertEqual(sum(stats.per_word_counts.values()), len(results))
        self.assertIn("rahul", stats.per_word_counts)
        self.assertIn("kumar", stats.per_word_counts)

    def test_combine_tracked_as_its_own_source(self):
        words = ["rahul", "kumar"]
        rs = RuleSet(case_modes=["lower"], combine_words=True)
        stats = GenerationStats(requested=1000)
        list(deduplicating_stream(words, rs, limit=1000, stats=stats))
        self.assertIn("combine", stats.per_word_counts)


class TestOutputFormats(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_infer_txt_default(self):
        self.assertEqual(infer_output_format("result.txt", None), "txt")
        self.assertEqual(infer_output_format("result", None), "txt")

    def test_infer_csv_from_extension(self):
        self.assertEqual(infer_output_format("result.csv", None), "csv")

    def test_infer_jsonl_from_extension(self):
        self.assertEqual(infer_output_format("result.jsonl", None), "jsonl")
        self.assertEqual(infer_output_format("result.json", None), "jsonl")

    def test_explicit_format_overrides_extension(self):
        self.assertEqual(infer_output_format("result.txt", "csv"), "csv")

    def test_csv_output_has_header_and_rows(self):
        path = os.path.join(self.tmpdir, "out.csv")
        write_stream_to_file(iter(["a1", "b2"]), path, output_format="csv")
        content = open(path, newline="").read()
        lines = content.strip().split("\r\n") if "\r\n" in content else content.strip().split("\n")
        self.assertEqual(lines[0], "candidate")
        self.assertIn("a1", lines)
        self.assertIn("b2", lines)

    def test_jsonl_output_is_one_json_object_per_line(self):
        path = os.path.join(self.tmpdir, "out.jsonl")
        write_stream_to_file(iter(["a1", "b2"]), path, output_format="jsonl")
        lines = [l for l in open(path).read().splitlines() if l]
        self.assertEqual(len(lines), 2)
        parsed = [json.loads(l) for l in lines]
        self.assertEqual([p["candidate"] for p in parsed], ["a1", "b2"])

    def test_valid_output_formats_constant(self):
        self.assertEqual(set(VALID_OUTPUT_FORMATS), {"txt", "csv", "jsonl"})


class TestSortCandidates(unittest.TestCase):
    def test_length_asc(self):
        result = sort_candidates(iter(["bbb", "a", "cc"]), "length-asc")
        self.assertEqual(result, ["a", "cc", "bbb"])

    def test_length_desc(self):
        result = sort_candidates(iter(["bbb", "a", "cc"]), "length-desc")
        self.assertEqual(result, ["bbb", "cc", "a"])

    def test_alpha(self):
        result = sort_candidates(iter(["banana", "apple", "cherry"]), "alpha")
        self.assertEqual(result, ["apple", "banana", "cherry"])


class TestResumeSupport(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.out_path = os.path.join(self.tmpdir, "result.txt")
        self.words = ["rahul"]
        self.rs = RuleSet(case_modes=["lower", "upper"], numbers=[str(n) for n in range(50)])
        self.rs_repr = repr(self.rs)

    def test_no_resume_state_returns_none(self):
        state = load_resume_state(self.out_path, self.words, self.rs_repr, 100)
        self.assertIsNone(state)

    def test_full_resume_cycle_produces_no_duplicates_and_no_gaps(self):
        stats1 = GenerationStats(requested=100)
        stream1 = deduplicating_stream(self.words, self.rs, limit=30, stats=stats1)
        write_stream_to_file(stream1, self.out_path)
        save_resume_state(self.out_path, self.words, self.rs_repr, 100, written=30)

        state = load_resume_state(self.out_path, self.words, self.rs_repr, 100)
        self.assertEqual(state.written, 30)

        stats2 = GenerationStats(requested=100)
        remaining = 100 - state.written
        stream2 = deduplicating_stream(self.words, self.rs, limit=remaining, stats=stats2, skip=state.written)
        write_stream_to_file(stream2, self.out_path, append=True)
        clear_resume_state(self.out_path)

        lines = [l.strip() for l in open(self.out_path)]
        self.assertEqual(len(lines), 100)
        self.assertEqual(len(set(lines)), 100)  # no duplicates introduced by resume
        self.assertFalse(os.path.exists(resume_path_for(self.out_path)))

    def test_mismatched_words_raise_on_resume(self):
        save_resume_state(self.out_path, self.words, self.rs_repr, 100, written=10)
        with open(self.out_path, "w") as f:
            f.write("placeholder\n" * 10)
        with self.assertRaises(OutputError):
            load_resume_state(self.out_path, ["different_word"], self.rs_repr, 100)

    def test_missing_output_file_raises_on_resume(self):
        save_resume_state(self.out_path, self.words, self.rs_repr, 100, written=10)
        # self.out_path was never actually created
        with self.assertRaises(OutputError):
            load_resume_state(self.out_path, self.words, self.rs_repr, 100)


if __name__ == "__main__":
    unittest.main()
