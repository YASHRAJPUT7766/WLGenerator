"""Screen renderers: preview, dry-run plan, and completion statistics."""
from __future__ import annotations

from ui.theme import C, PRIMARY, ACCENT, MUTED, SUCCESS, style
from ui.banner import section_title, complete_banner, kv_line
from utils.formatting import human_count, human_size, human_duration
from rules.definitions import RuleSet
from output.stats import RunStats


def render_preview(
    seed_words,
    ruleset: RuleSet,
    estimated_total: int,
    preview_entries: list[str],
    output_path: str | None,
    max_preview: int = 15,
) -> str:
    lines = [section_title("PREVIEW"), ""]
    lines.append(kv_line("Source words", human_count(len(seed_words.words)), label_width=22))
    lines.append(kv_line("Enabled rules", ", ".join(ruleset.enabled_categories()) or "none", label_width=22))
    lines.append(kv_line("Estimated candidates", human_count(estimated_total), label_width=22))
    lines.append(kv_line("Output target", output_path or "(not specified)", label_width=22))
    lines.append("")
    lines.append(style("  Preview entries:", C.BOLD))
    shown = preview_entries[:max_preview]
    for entry in shown:
        lines.append(f"    {style('•', MUTED)} {entry}")
    if estimated_total > len(shown):
        lines.append(f"    {style(f'… and approximately {human_count(estimated_total - len(shown))} more', MUTED)}")
    return "\n".join(lines)


def render_dry_run(
    seed_words,
    ruleset: RuleSet,
    requested: int,
    estimated_size_bytes: int,
    output_path: str,
) -> str:
    lines = [section_title("GENERATION PLAN"), ""]
    lines.append(kv_line("Input words", human_count(len(seed_words.words))))
    lines.append(kv_line("Rules", str(ruleset.rule_count())))
    lines.append(kv_line("Rule categories", ", ".join(ruleset.enabled_categories()) or "none"))
    lines.append(kv_line("Requested count", human_count(requested)))
    lines.append(kv_line("Estimated size", human_size(estimated_size_bytes)))
    lines.append(kv_line("Output", output_path))
    lines.append("")
    lines.append(style("  No files were written (--dry-run).", MUTED))
    return "\n".join(lines)


def render_count_summary(requested: int, possible: int, generated: int, duplicates: int) -> str:
    lines = []
    lines.append(kv_line("Requested", human_count(requested)))
    lines.append(kv_line("Possible", human_count(possible)))
    lines.append(kv_line("Generated", human_count(generated)))
    lines.append(kv_line("Duplicates", human_count(duplicates)))
    if generated < requested:
        lines.append("")
        lines.append(style(
            "  Note: fewer unique candidates were possible than requested under\n"
            "  the current rule set. No entries were duplicated to fill the gap.",
            style("", "") + "\033[93m",
        ))
    return "\n".join(lines)


def render_completion(stats: RunStats, show_stats: bool = False) -> str:
    lines = [complete_banner(), ""]
    lines.append(kv_line("Input entries", human_count(stats.input_words)))
    lines.append(kv_line("Requested", human_count(stats.requested)))
    lines.append(kv_line("Generated", human_count(stats.generated)))
    lines.append(kv_line("Duplicates", human_count(stats.duplicates)))
    lines.append(kv_line("Rules enabled", human_count(stats.rules_enabled)))
    lines.append(kv_line("Output file", stats.output_file or "-"))
    lines.append(kv_line("File size", human_size(stats.file_size_bytes)))
    lines.append(kv_line("Time taken", human_duration(stats.time_taken_seconds)))
    lines.append(kv_line("Generation rate", f"{human_count(int(stats.generation_rate_per_sec))}/s"))
    if show_stats and stats.per_word_counts:
        lines.append("")
        lines.append(style("  Per-source breakdown:", C.BOLD))
        for source, count in sorted(stats.per_word_counts.items(), key=lambda kv: -kv[1]):
            lines.append(kv_line(f"  {source}", human_count(count), label_width=22))
    if stats.interrupted:
        lines.append("")
        lines.append(style("  ⚠ Generation was interrupted before completion.", "\033[93m"))
    return "\n".join(lines)


def render_large_operation_warning(requested: int, estimated_size_bytes: int) -> str:
    lines = []
    lines.append(style("  ⚠ Large operation warning", C.BOLD + "\033[93m"))
    lines.append(kv_line("Requested candidates", human_count(requested)))
    lines.append(kv_line("Estimated output size", human_size(estimated_size_bytes)))
    lines.append("")
    lines.append(style("  Continue? [y/N] ", C.BOLD))
    return "\n".join(lines)
