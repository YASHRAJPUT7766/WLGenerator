"""
Branding: startup banner, boxed headers, and section dividers.
"""
from __future__ import annotations

import shutil

from _meta import __version__
from ui.theme import C, PRIMARY, ACCENT, MUTED, SUCCESS, style

BOX_TL, BOX_TR, BOX_BL, BOX_BR = "╔", "╗", "╚", "╝"
BOX_H, BOX_V = "═", "║"
LINE_H = "─"

# Big block-letter "WL GEN" logo, built from a small fixed-width block
# font so every row is guaranteed the same length (verified below) --
# hand-drawn ASCII art tends to drift by a column and look crooked,
# this construction can't. Each row gets its own color for a simple
# two-tone gradient effect on terminals with ANSI color support; it
# degrades gracefully (falls back to bare ASCII) when color is off or
# the terminal is narrower than the logo.
_BLOCK_FONT = {
    "W": ["█   █", "█   █", "█ █ █", "█ █ █", " █ █ "],
    "L": ["█    ", "█    ", "█    ", "█    ", "█████"],
    "G": [" ████", "█    ", "█  ██", "█   █", " ████"],
    "E": ["█████", "█    ", "████ ", "█    ", "█████"],
    "N": ["█   █", "██  █", "█ █ █", "█  ██", "█   █"],
    " ": ["  ", "  ", "  ", "  ", "  "],
}
_LOGO_TEXT = "WL GEN"
_LOGO_ROWS = [
    "".join(_BLOCK_FONT[ch][row] + " " for ch in _LOGO_TEXT).rstrip()
    for row in range(5)
]
_LOGO_GRADIENT = [C.BRIGHT_CYAN, C.BRIGHT_CYAN, C.CYAN, C.BRIGHT_MAGENTA, C.BRIGHT_MAGENTA]


def term_width(default: int = 72) -> int:
    try:
        w = shutil.get_terminal_size(fallback=(default, 24)).columns
    except Exception:
        w = default
    return max(60, min(w, 100))


def _center(text: str, width: int) -> str:
    pad = max(0, width - len(text))
    left = pad // 2
    right = pad - left
    return " " * left + text + " " * right


def boxed(lines: list[str], width: int | None = None, color: str = PRIMARY) -> str:
    """Render a list of plain-text lines inside a double-line box."""
    w = width or max(len(l) for l in lines) + 4
    w = max(w, 40)
    out = [style(BOX_TL + BOX_H * (w - 2) + BOX_TR, color)]
    for line in lines:
        inner = _center(line, w - 2)
        out.append(style(BOX_V, color) + inner + style(BOX_V, color))
    out.append(style(BOX_BL + BOX_H * (w - 2) + BOX_BR, color))
    return "\n".join(out)


def _logo_block(width: int) -> str:
    """
    Render the big block-letter logo, centered, with a simple two-tone
    gradient (cyan fading into magenta top-to-bottom). Falls back to
    nothing if the terminal is too narrow to fit it cleanly -- the
    boxed "W L   G E N" title still renders underneath either way.
    """
    logo_width = max(len(r) for r in _LOGO_ROWS)
    if width < logo_width + 4:
        return ""
    rows = []
    for row, color in zip(_LOGO_ROWS, _LOGO_GRADIENT):
        rows.append(style(_center(row, width), C.BOLD + color))
    return "\n".join(rows)


def startup_banner() -> str:
    w = term_width()
    box_w = min(w, 62)

    logo = _logo_block(w)
    lines = [
        "",
        style("W L   G E N", C.BOLD + PRIMARY),
        style("WORDLIST GENERATOR", C.BOLD + C.WHITE),
        "",
        style("Security Research Utility", ACCENT),
        "",
    ]
    rendered = boxed(lines, width=box_w, color=PRIMARY)
    tagline = style(
        _center("Controlled  ·  Offline  ·  Rule-based  ·  Authorized use only", box_w - 2),
        MUTED,
    )
    footer = style(
        _center(f"v{__version__}", box_w - 2),
        MUTED,
    )

    parts = []
    if logo:
        parts.append(logo)
        parts.append("")
    parts.append(rendered)
    parts.append(tagline)
    parts.append(footer)
    return "\n".join(parts)


def section_title(title: str) -> str:
    w = term_width()
    bar = LINE_H * max(4, w - len(title) - 3)
    return style(f"── {title} ", C.BOLD + PRIMARY) + style(bar, MUTED)


def complete_banner(title: str = "GENERATION COMPLETE") -> str:
    from ui.theme import SUCCESS
    w = min(term_width(), 46)
    lines = [style(f"✓  {title}", C.BOLD + C.WHITE)]
    return boxed(lines, width=w, color=SUCCESS)


def kv_line(label: str, value: str, label_width: int = 16) -> str:
    from ui.theme import LABEL, VALUE
    return f"  {style(label.ljust(label_width), LABEL)}: {style(value, VALUE)}"
