"""
Complete flag specification for WL Gen.

Organized into categories that mirror the help-screen sections:
INPUT, GENERATION, TRANSFORMATION, OUTPUT, DISPLAY, CONFIGURATION, UTILITY.
"""
from __future__ import annotations

from cli.parser import ArgParser, FlagSpec, FLAG, VALUE, REPEATED

FLAG_SPECS: list[FlagSpec] = [
    # --- INPUT OPTIONS ---
    FlagSpec("wordlist", ["-w"], ["--wordlist"], VALUE,
             "Use an existing local wordlist file as input", "FILE", "INPUT OPTIONS"),
    FlagSpec("word", ["-wd"], ["--word"], REPEATED,
             "Provide one or more custom source words (repeatable)", "WORD", "INPUT OPTIONS"),
    FlagSpec("encoding", [], ["--encoding"], VALUE,
             "Text encoding for reading input files (default: utf-8)", "ENC", "INPUT OPTIONS"),

    # --- GENERATION OPTIONS ---
    FlagSpec("generate", ["-g"], ["--generate"], FLAG,
             "Generate a controlled test wordlist", "", "GENERATION OPTIONS"),
    FlagSpec("count", ["-n"], ["--count"], VALUE,
             "Requested number of generated candidates", "N", "GENERATION OPTIONS"),
    FlagSpec("random", ["-r"], ["--random"], FLAG,
             "Enable controlled random test-data mode", "", "GENERATION OPTIONS"),
    FlagSpec("charset", [], ["--charset"], VALUE,
             "Character set for random mode (alnum/alpha/lower/upper/digits/full/custom)",
             "SET", "GENERATION OPTIONS"),
    FlagSpec("length", ["-l"], ["--length"], VALUE,
             "Permitted length (random mode) or length filter (word mode, 'min:max')",
             "N|MIN:MAX", "GENERATION OPTIONS"),
    FlagSpec("combine", [], ["--combine"], FLAG,
             "Combine pairs of supplied source words", "", "GENERATION OPTIONS"),
    FlagSpec("all_rules", [], ["--all"], FLAG,
             "Enable every rule category, auto-scaled to fit -n (this is the default "
             "when no other rule flag is given)", "", "GENERATION OPTIONS"),

    # --- TRANSFORMATION OPTIONS ---
    FlagSpec("prefix", ["-p"], ["--prefix"], REPEATED,
             "Add a prefix to apply (repeatable)", "TEXT", "TRANSFORMATION OPTIONS"),
    FlagSpec("suffix", ["-s"], ["--suffix"], REPEATED,
             "Add a suffix to apply (repeatable)", "TEXT", "TRANSFORMATION OPTIONS"),
    FlagSpec("numbers", ["-N"], ["--numbers"], VALUE,
             "Numeric suffixes: comma list (1,123,2025) and/or range:START-END",
             "LIST", "TRANSFORMATION OPTIONS"),
    FlagSpec("pad_numbers", [], ["--pad"], FLAG,
             "Zero-pad numbers from a range to a fixed width (e.g. 00..99)",
             "", "TRANSFORMATION OPTIONS"),
    FlagSpec("symbols", ["-S"], ["--symbols"], VALUE,
             "Comma-separated symbol suffixes (e.g. !,@,#)", "LIST", "TRANSFORMATION OPTIONS"),
    FlagSpec("case", ["-c"], ["--case"], VALUE,
             "Comma-separated case modes: lower,upper,capitalize,title", "LIST", "TRANSFORMATION OPTIONS"),
    FlagSpec("separator", ["-x"], ["--separator"], VALUE,
             "Comma-separated separators used between prefix/word/suffix", "LIST", "TRANSFORMATION OPTIONS"),
    FlagSpec("substitutions", [], ["--leet"], FLAG,
             "Enable controlled leetspeak-style character substitutions", "", "TRANSFORMATION OPTIONS"),
    FlagSpec("deduplicate", ["-d"], ["--deduplicate"], FLAG,
             "Remove duplicate candidates (on by default)", "", "TRANSFORMATION OPTIONS"),
    FlagSpec("no_deduplicate", [], ["--no-dedupe"], FLAG,
             "Disable deduplication", "", "TRANSFORMATION OPTIONS"),
    FlagSpec("dedupe_ci", [], ["--dedupe-ci"], FLAG,
             "Deduplicate case-insensitively (\"Yash1\" and \"YASH1\" count as one)",
             "", "TRANSFORMATION OPTIONS"),

    # --- OUTPUT OPTIONS ---
    FlagSpec("output", ["-o"], ["--output"], VALUE,
             "Output file path", "FILE", "OUTPUT OPTIONS"),
    FlagSpec("force", ["-f"], ["--force"], FLAG,
             "Overwrite output file without prompting", "", "OUTPUT OPTIONS"),
    FlagSpec("json_stats", [], ["--json"], VALUE,
             "Write machine-readable JSON statistics to a file", "FILE", "OUTPUT OPTIONS"),
    FlagSpec("output_format", [], ["--format"], VALUE,
             "Output file format: txt (default), csv, or jsonl. "
             "Inferred from --output's extension if not given.",
             "FORMAT", "OUTPUT OPTIONS"),
    FlagSpec("sort", [], ["--sort"], VALUE,
             "Sort output: length-asc, length-desc, or alpha (default: unsorted, streamed)",
             "MODE", "OUTPUT OPTIONS"),
    FlagSpec("resume", [], ["--resume"], FLAG,
             "Resume an interrupted run, appending to the existing output file",
             "", "OUTPUT OPTIONS"),

    # --- DISPLAY OPTIONS ---
    FlagSpec("preview", ["-P"], ["--preview"], FLAG,
             "Preview the generation result without writing full output", "", "DISPLAY OPTIONS"),
    FlagSpec("stats", [], ["--stats"], FLAG,
             "Display detailed generation statistics", "", "DISPLAY OPTIONS"),
    FlagSpec("dry_run", [], ["--dry-run"], FLAG,
             "Calculate the generation plan without creating the file", "", "DISPLAY OPTIONS"),
    FlagSpec("quiet", ["-q"], ["--quiet"], FLAG,
             "Suppress non-essential output", "", "DISPLAY OPTIONS"),
    FlagSpec("no_color", [], ["--no-color"], FLAG,
             "Disable colored output", "", "DISPLAY OPTIONS"),
    FlagSpec("yes", ["-y"], ["--yes"], FLAG,
             "Automatically confirm large-operation prompts", "", "DISPLAY OPTIONS"),

    # --- CONFIGURATION OPTIONS ---
    FlagSpec("config", [], ["--config"], VALUE,
             "Load a custom TOML configuration file", "FILE", "CONFIGURATION OPTIONS"),
    FlagSpec("rules", [], ["--rules"], FLAG,
             "Display available generation rule categories", "", "CONFIGURATION OPTIONS"),

    # --- UTILITY OPTIONS ---
    FlagSpec("check", ["-k"], ["--check"], VALUE,
             "Analyze the strength of a local password string", "PASSWORD", "UTILITY OPTIONS"),
    FlagSpec("version", [], ["--version"], FLAG,
             "Display the current version", "", "UTILITY OPTIONS"),
    FlagSpec("help", ["-h"], ["--help"], FLAG,
             "Display complete help", "", "UTILITY OPTIONS"),
    FlagSpec("debug", [], ["--debug"], FLAG,
             "Show full tracebacks on error", "", "UTILITY OPTIONS"),
]


def build_parser() -> ArgParser:
    return ArgParser(FLAG_SPECS)


HELP_SECTIONS_ORDER = [
    "INPUT OPTIONS",
    "GENERATION OPTIONS",
    "TRANSFORMATION OPTIONS",
    "OUTPUT OPTIONS",
    "DISPLAY OPTIONS",
    "CONFIGURATION OPTIONS",
    "UTILITY OPTIONS",
]
