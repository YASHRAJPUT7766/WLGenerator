"""Categorized, colorized help screen."""
from __future__ import annotations

from _meta import __version__
from cli.flags import FLAG_SPECS, HELP_SECTIONS_ORDER
from ui.theme import C, PRIMARY, ACCENT, MUTED, style
from ui.banner import startup_banner, term_width

EXAMPLES = [
    ("wlgen", "Show the startup interface"),
    ("wlgen -g -wd Yash -n 10000 -o result.txt", "Generate 10,000 candidates (all rules on by default)"),
    ("wlgen -g -wd Yash -wd Kumar -n 100000", "Multiple words, still fully automatic"),
    ("wlgen -g -w words.txt", "Generate from an existing wordlist file"),
    ("wlgen -g -w words.txt -wd Yash", "Combine a wordlist with extra words"),
    ("wlgen -g -wd Yash -P", "Preview candidates without full generation"),
    ("wlgen -g -wd Yash -n 1000000 --dry-run", "Show the generation plan only"),
    ("wlgen -g -wd Yash -c lower,capitalize -N 1,123,2025", "Hand-pick specific rules instead of --all"),
    ("wlgen -g -wd Yash -N range:0-9999 -n 10000 -o out.txt", "Auto-try every number 0-9999 as a suffix"),
    ("wlgen -g -wd Yash -N range:0-99:1 --pad -n 100 -o pins.txt", "Zero-padded PIN range: 00, 01, ... 99"),
    ("wlgen -g -wd Yash -N 1,12,range:2000-2025", "Mix explicit numbers with a range"),
    ("wlgen -r -l 12 -n 5000 -o random.txt", "Random mode: 5,000 12-char strings"),
    ("wlgen -k 'Summer2024!'", "Check local password strength"),
    ("wlgen -g -wd Yash --config myconfig.toml", "Generate using a config file"),
]


def _fmt_flag_tokens(spec) -> str:
    tokens = spec.short + spec.long
    return ", ".join(tokens)


def render_help() -> str:
    lines = []
    lines.append(startup_banner())
    lines.append("")
    lines.append(style("USAGE", C.BOLD + ACCENT))
    lines.append(f"  wlgen [OPTIONS]")
    lines.append("")

    by_category: dict[str, list] = {cat: [] for cat in HELP_SECTIONS_ORDER}
    for spec in FLAG_SPECS:
        by_category.setdefault(spec.category, []).append(spec)

    # Compute alignment width across all flags for a clean layout
    token_strs = [_fmt_flag_tokens(s) for s in FLAG_SPECS]
    col_width = min(max(len(t) for t in token_strs) + 2, 28)

    for category in HELP_SECTIONS_ORDER:
        specs = by_category.get(category, [])
        if not specs:
            continue
        lines.append(style(category, C.BOLD + PRIMARY))
        for spec in specs:
            tokens = _fmt_flag_tokens(spec)
            tokens_colored = style(tokens.ljust(col_width), C.CYAN)
            metavar = f" {style(spec.metavar, MUTED)}" if spec.metavar else ""
            lines.append(f"  {tokens_colored}{spec.help}{metavar}")
        lines.append("")

    lines.append(style("EXAMPLES", C.BOLD + ACCENT))
    for cmd, desc in EXAMPLES:
        lines.append(f"  {style('$', MUTED)} {style(cmd, C.WHITE + C.BOLD)}")
        lines.append(f"      {style(desc, MUTED)}")
    lines.append("")
    lines.append(style(
        "Safety boundary: WL Gen operates only on local, user-supplied data.\n"
        "It does not perform authentication attempts, CAPTCHA/lockout bypass,\n"
        "or attacks against remote systems. For authorized testing and\n"
        "defensive research only.",
        MUTED,
    ))
    return "\n".join(lines)


def render_version() -> str:
    return f"WL Gen version {style(__version__, C.BOLD + PRIMARY)}"


def render_rules_list() -> str:
    lines = [style("AVAILABLE GENERATION RULE CATEGORIES", C.BOLD + PRIMARY), ""]
    rule_docs = [
        ("case", "lower, upper, capitalize, title"),
        ("prefix", "prepend one or more fixed strings"),
        ("suffix", "append one or more fixed strings"),
        ("numbers", "append numeric sequences (e.g. 1, 123, 2025, or range:0-9999)"),
        ("symbols", "append symbol characters (e.g. !, @, #)"),
        ("separators", "characters joining prefix/word/suffix segments"),
        ("substitutions", "controlled leetspeak-style character swaps"),
        ("combinations", "pairwise concatenation of multiple source words"),
        ("length filter", "restrict output to a min/max length range"),
        ("deduplicate", "remove duplicate candidates (on by default)"),
    ]
    width = max(len(n) for n, _ in rule_docs) + 2
    for name, desc in rule_docs:
        lines.append(f"  {style(name.ljust(width), C.CYAN)}{desc}")
    return "\n".join(lines)
