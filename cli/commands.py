"""
Command handlers: the orchestration layer between parsed CLI args and
the underlying generator/output/checker modules.
"""
from __future__ import annotations

import sys
import time

from cli.parser import ParsedArgs
from cli.resolve import resolve_ruleset, parse_count, parse_length_option, check_flag_compatibility
from cli.display import (
    render_preview, render_dry_run, render_completion,
    render_large_operation_warning, render_count_summary,
)
from cli.help import render_rules_list
from config.loader import load_config
from input.sources import collect_seed_words
from generator.engine import deduplicating_stream, GenerationStats, count_full_space
from generator.random_mode import RandomModeConfig, stream_random_candidates, CHARSET_PRESETS
from output.writer import write_stream_to_file, estimate_output_bytes, WriteInterrupted
from output.stats import RunStats
from checker.strength import analyze_password
from ui.progress import ProgressBar
from ui.theme import C, PRIMARY, SUCCESS, WARNING, ERROR, MUTED, style
from ui.banner import section_title
from utils.errors import ArgumentError, OutputError, InterruptedGeneration
from utils.system import check_sufficient_space
from utils.formatting import human_count, human_size

DEFAULT_PREVIEW_COUNT = 15
DEFAULT_OUTPUT_FILE = "wordlist.txt"
LARGE_OPERATION_THRESHOLD = 250_000


def _print(text: str = "", quiet: bool = False):
    if not quiet:
        print(text)


def cmd_generate(args: ParsedArgs):
    check_flag_compatibility(args)

    config = None
    if args.get("config"):
        config = load_config(args.get("config"))

    quiet = bool(args.get("quiet"))
    seed_words = collect_seed_words(
        cli_words=args.get("word"),
        wordlist_path=args.get("wordlist"),
        encoding=args.get("encoding") or "utf-8",
    )
    requested = parse_count(args.get("count")) or 1000
    ruleset = resolve_ruleset(args, config, word_count=seed_words.count, requested=requested)

    output_path = args.get("output") or DEFAULT_OUTPUT_FILE

    if args.get("rules"):
        print(render_rules_list())
        return

    if args.get("preview"):
        _run_preview(seed_words, ruleset, requested, output_path)
        return

    if args.get("dry_run"):
        _run_dry_run(seed_words, ruleset, requested, output_path)
        return

    _run_full_generation(seed_words, ruleset, requested, output_path, args)


def _run_preview(seed_words, ruleset, requested, output_path):
    from generator.engine import deduplicating_stream
    from rules.engine import estimate_candidate_space

    estimated = estimate_candidate_space(seed_words.words, ruleset)
    preview_entries = []
    for candidate in deduplicating_stream(seed_words.words, ruleset, limit=DEFAULT_PREVIEW_COUNT):
        preview_entries.append(candidate)

    print(render_preview(seed_words, ruleset, estimated, preview_entries, output_path))


def _run_dry_run(seed_words, ruleset, requested, output_path):
    from rules.engine import estimate_candidate_space, build_variant_pool

    estimated_total = estimate_candidate_space(seed_words.words, ruleset)
    effective_count = min(requested, estimated_total) if estimated_total else requested

    sample = []
    if seed_words.words:
        sample = build_variant_pool(seed_words.words[0], ruleset)[:20]
    estimated_bytes = estimate_output_bytes(sample or ["placeholder"], effective_count)

    print(render_dry_run(seed_words, ruleset, requested, estimated_bytes, output_path))


def _prompt_yes_no(prompt_text: str, default_no: bool = True) -> bool:
    """
    Ask a yes/no question, but never block indefinitely: if stdin is not
    an interactive terminal (e.g. piped, redirected, or absent), treat
    that as a 'no' immediately rather than hanging on input().
    """
    if not sys.stdin.isatty():
        return False
    print(prompt_text, end="")
    try:
        answer = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("y", "yes")


def _confirm_large_operation(requested: int, estimated_bytes: int, auto_yes: bool) -> bool:
    if requested < LARGE_OPERATION_THRESHOLD:
        return True
    if auto_yes:
        return True
    print(render_large_operation_warning(requested, estimated_bytes))
    if not sys.stdin.isatty():
        print(style(
            "  No interactive terminal detected — not proceeding automatically.\n"
            "  Re-run with -y/--yes to confirm large operations non-interactively.",
            MUTED,
        ))
        return False
    try:
        answer = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("y", "yes")


def _run_full_generation(seed_words, ruleset, requested, output_path, args):
    from rules.engine import estimate_candidate_space, build_variant_pool
    from utils.system import ensure_writable_path
    from output.writer import infer_output_format, sort_candidates, VALID_OUTPUT_FORMATS
    from output.stats import RunStats as _RunStats  # noqa: F401 (already imported above; kept local for clarity)
    from generator.resume import (
        load_resume_state, save_resume_state, clear_resume_state,
    )
    import os

    quiet = bool(args.get("quiet"))
    force = bool(args.get("force"))
    resume_requested = bool(args.get("resume"))

    output_format = args.get("output_format")
    if output_format and output_format not in VALID_OUTPUT_FORMATS:
        raise ArgumentError(
            f"Invalid --format value '{output_format}'. Use one of: "
            f"{', '.join(VALID_OUTPUT_FORMATS)}."
        )
    output_format = infer_output_format(output_path, output_format)

    sort_mode = args.get("sort")
    if sort_mode and sort_mode not in ("length-asc", "length-desc", "alpha"):
        raise ArgumentError(
            f"Invalid --sort value '{sort_mode}'. Use one of: length-asc, length-desc, alpha."
        )

    ruleset_repr = repr(ruleset)
    resume_skip = 0
    append_mode = False

    if resume_requested:
        resume_state = load_resume_state(output_path, seed_words.words, ruleset_repr, requested)
        if resume_state is None:
            _print(style(
                f"No resume state found for '{output_path}' -- starting a fresh run.",
                MUTED,
            ), quiet)
        else:
            resume_skip = resume_state.written
            append_mode = True
            _print(style(
                f"Resuming: {human_count(resume_skip)} candidates already written, "
                f"continuing from there.",
                MUTED,
            ), quiet)
    elif os.path.exists(output_path) and not force:
        should_overwrite = _prompt_yes_no(
            style(f"Output file '{output_path}' already exists. Overwrite? [y/N] ", C.BOLD)
        )
        if not sys.stdin.isatty():
            print(style(
                f"Output file '{output_path}' already exists and no interactive "
                f"terminal was detected. Use -f/--force to overwrite non-interactively.",
                MUTED,
            ))
        if not should_overwrite:
            print(style("Aborted. Use -f/--force to overwrite without prompting.", MUTED))
            return

    ensure_writable_path(output_path)

    estimated_total = estimate_candidate_space(seed_words.words, ruleset)
    sample = build_variant_pool(seed_words.words[0], ruleset)[:20] if seed_words.words else []
    remaining_requested = max(requested - resume_skip, 0)
    estimated_bytes = estimate_output_bytes(
        sample or ["placeholder"], min(remaining_requested, max(estimated_total, 1))
    )

    if remaining_requested == 0:
        _print(style(
            f"Nothing to resume -- {human_count(resume_skip)} candidates were already "
            f"written, which already meets or exceeds the requested count "
            f"({human_count(requested)}).",
            MUTED,
        ), quiet)
        clear_resume_state(output_path)
        return

    if not _confirm_large_operation(remaining_requested, estimated_bytes, bool(args.get("yes"))):
        print(style("Aborted by user.", MUTED))
        return

    check_sufficient_space(output_path, estimated_bytes)

    stats = GenerationStats(requested=requested, input_words=seed_words.count,
                             rules_enabled=ruleset.rule_count())

    _print(section_title("GENERATING"), quiet)
    _print("", quiet)

    progress = ProgressBar(total=remaining_requested, label="Generating") if not quiet else None
    start = time.monotonic()
    interrupted = False

    def progress_cb(count, bytes_written):
        if progress:
            progress.update(count, bytes_written)

    ran_out_of_space = False
    try:
        candidate_stream = deduplicating_stream(
            seed_words.words, ruleset, limit=remaining_requested, stats=stats, skip=resume_skip,
        )
        if sort_mode:
            # Sorting needs the full set materialized first; this trades
            # the usual constant-memory streaming write for the ordering
            # the user explicitly asked for.
            sorted_candidates = sort_candidates(candidate_stream, sort_mode)
            total_written, total_bytes = write_stream_to_file(
                iter(sorted_candidates), output_path,
                encoding=args.get("encoding") or "utf-8",
                progress_callback=progress_cb,
                output_format=output_format,
                append=append_mode,
            )
        else:
            total_written, total_bytes = write_stream_to_file(
                candidate_stream, output_path,
                encoding=args.get("encoding") or "utf-8",
                progress_callback=progress_cb,
                output_format=output_format,
                append=append_mode,
            )
        if stats.generated < remaining_requested:
            ran_out_of_space = True
    except WriteInterrupted as exc:
        interrupted = True
        total_written, total_bytes = exc.written_count, exc.written_bytes
        if progress:
            progress.finish(interrupted=True)
        save_resume_state(
            output_path, seed_words.words, ruleset_repr, requested,
            written=resume_skip + total_written,
        )
        _print(style(
            "\n  Generation interrupted. Partial output was saved.\n"
            "  Re-run the same command with --resume to continue from here.",
            WARNING,
        ), quiet)
    else:
        if progress:
            progress.finish(interrupted=False)

    elapsed = time.monotonic() - start

    # If we exhausted the candidate space before reaching the requested
    # count, compute the exact ceiling for accurate "Possible" reporting.
    possible = stats.possible
    if ran_out_of_space and not interrupted:
        possible = count_full_space(seed_words.words, ruleset)

    if not interrupted:
        # A full (non-interrupted) run has nothing left to resume.
        clear_resume_state(output_path)

    total_generated_overall = resume_skip + total_written

    run_stats = RunStats(
        mode="generate",
        input_words=seed_words.count,
        requested=requested,
        generated=total_generated_overall,
        duplicates=stats.duplicates,
        possible=possible + resume_skip,
        rules_enabled=ruleset.rule_count(),
        output_file=output_path,
        file_size_bytes=total_bytes,
        time_taken_seconds=elapsed,
        interrupted=interrupted,
        per_word_counts=stats.per_word_counts,
    )
    run_stats.finalize_rate()

    _print("", quiet)
    if total_generated_overall < requested and not interrupted:
        _print(render_count_summary(requested, possible + resume_skip, total_generated_overall, stats.duplicates), quiet)
        _print("", quiet)

    _print(render_completion(run_stats, show_stats=bool(args.get("stats"))), quiet)

    if args.get("json_stats"):
        run_stats.write_json_file(args.get("json_stats"))
        _print(f"\n  JSON statistics written to {args.get('json_stats')}", quiet)


def cmd_random(args: ParsedArgs):
    check_flag_compatibility(args)
    quiet = bool(args.get("quiet"))

    length_val, _ = parse_length_option(args.get("length"), random_mode=True)
    length = length_val or 12
    requested = parse_count(args.get("count")) or 1000
    charset = args.get("charset") or "alnum"
    output_path = args.get("output") or "random_data.txt"

    if charset not in CHARSET_PRESETS and len(charset) < 2:
        raise ArgumentError(
            f"Invalid --charset value '{charset}'. Use one of "
            f"{', '.join(CHARSET_PRESETS)} or provide a custom character string."
        )

    config = RandomModeConfig(
        length=length,
        count=requested,
        charset=charset,
        deduplicate=not bool(args.get("no_deduplicate")),
    )

    if args.get("preview"):
        sample = []
        for i, cand in enumerate(stream_random_candidates(
                RandomModeConfig(length=length, count=DEFAULT_PREVIEW_COUNT, charset=charset))):
            sample.append(cand)
        print(section_title("RANDOM MODE PREVIEW"))
        print()
        print(f"  Length          : {length}")
        print(f"  Character set   : {charset}")
        print(f"  Requested count : {human_count(requested)}")
        print()
        for s in sample:
            print(f"    • {s}")
        return

    if args.get("dry_run"):
        avg_size = (length + 1) * requested
        print(section_title("RANDOM MODE GENERATION PLAN"))
        print()
        print(f"  Length          : {length}")
        print(f"  Character set   : {charset}")
        print(f"  Requested count : {human_count(requested)}")
        print(f"  Estimated size  : {human_size(avg_size)}")
        print(f"  Output          : {output_path}")
        print()
        print(style("  No files were written (--dry-run).", MUTED))
        return

    estimated_bytes = (length + 1) * requested
    if not _confirm_large_operation(requested, estimated_bytes, bool(args.get("yes"))):
        print(style("Aborted by user.", MUTED))
        return

    check_sufficient_space(output_path, estimated_bytes)

    _print(section_title("GENERATING (RANDOM MODE)"), quiet)
    _print("", quiet)

    progress = ProgressBar(total=requested, label="Generating") if not quiet else None
    start = time.monotonic()
    interrupted = False

    def progress_cb(count, bytes_written):
        if progress:
            progress.update(count, bytes_written)

    try:
        total_written, total_bytes = write_stream_to_file(
            stream_random_candidates(config), output_path,
            progress_callback=progress_cb,
        )
    except KeyboardInterrupt:
        interrupted = True
        total_written, total_bytes = 0, 0
        if progress:
            progress.finish(interrupted=True)
    else:
        if progress:
            progress.finish(interrupted=False)

    elapsed = time.monotonic() - start
    run_stats = RunStats(
        mode="random",
        input_words=0,
        requested=requested,
        generated=total_written,
        duplicates=0,
        possible=total_written,
        rules_enabled=0,
        output_file=output_path,
        file_size_bytes=total_bytes,
        time_taken_seconds=elapsed,
        interrupted=interrupted,
    )
    run_stats.finalize_rate()
    _print("", quiet)
    _print(render_completion(run_stats), quiet)


def cmd_check(password: str):
    report = analyze_password(password)
    verdict_color = {
        "Very Weak": ERROR, "Weak": ERROR, "Moderate": WARNING,
        "Strong": SUCCESS, "Very Strong": SUCCESS,
    }.get(report.verdict, C.WHITE)

    print(section_title("PASSWORD STRENGTH ANALYSIS"))
    print()
    print(f"  {'Length'.ljust(22)}: {report.password_length}")
    print(f"  {'Character set size'.ljust(22)}: {report.charset_size}")
    print(f"  {'Estimated entropy'.ljust(22)}: {report.entropy_bits} bits")
    print(f"  {'Diversity score'.ljust(22)}: {report.diversity_score}/4")
    print(f"  {'Lowercase'.ljust(22)}: {'yes' if report.has_lower else 'no'}")
    print(f"  {'Uppercase'.ljust(22)}: {'yes' if report.has_upper else 'no'}")
    print(f"  {'Digits'.ljust(22)}: {'yes' if report.has_digit else 'no'}")
    print(f"  {'Symbols'.ljust(22)}: {'yes' if report.has_symbol else 'no'}")
    print(f"  {'Repetition detected'.ljust(22)}: {'yes' if report.repetition_detected else 'no'}")
    print(f"  {'Sequential pattern'.ljust(22)}: {'yes' if report.sequential_detected else 'no'}")
    print(f"  {'Common weak password'.ljust(22)}: {'yes' if report.common_password_match else 'no'}")
    if report.predictable_pattern_notes:
        print(f"  {'Pattern notes'.ljust(22)}:")
        for note in report.predictable_pattern_notes:
            print(f"      - {note}")
    print(f"  {'Est. offline crack time'.ljust(22)}: {report.estimated_crack_time}")
    print()
    print(f"  Verdict: {style(report.verdict, C.BOLD + verdict_color)}")
    print()
    print(style("  Analyzed locally. Nothing was transmitted or stored.", MUTED))
