"""
Terminal color theme and low-level ANSI helpers.

Pure ANSI escape codes are used (via colorama for Windows compatibility)
so the tool has zero heavyweight UI dependencies while still looking
professional on any modern terminal.
"""
from __future__ import annotations

import os
import sys

try:
    import colorama
    colorama.init(autoreset=False)
    _COLORAMA_AVAILABLE = True
except ImportError:  # pragma: no cover
    _COLORAMA_AVAILABLE = False


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("WLGEN_FORCE_COLOR") is not None:
        return True
    if not sys.stdout.isatty():
        return False
    return True


COLOR_ENABLED = _supports_color()


class C:
    """ANSI color/style codes. Empty strings when color is disabled."""
    RESET = "\033[0m" if COLOR_ENABLED else ""
    BOLD = "\033[1m" if COLOR_ENABLED else ""
    DIM = "\033[2m" if COLOR_ENABLED else ""
    ITALIC = "\033[3m" if COLOR_ENABLED else ""
    UNDERLINE = "\033[4m" if COLOR_ENABLED else ""

    BLACK = "\033[30m" if COLOR_ENABLED else ""
    RED = "\033[31m" if COLOR_ENABLED else ""
    GREEN = "\033[32m" if COLOR_ENABLED else ""
    YELLOW = "\033[33m" if COLOR_ENABLED else ""
    BLUE = "\033[34m" if COLOR_ENABLED else ""
    MAGENTA = "\033[35m" if COLOR_ENABLED else ""
    CYAN = "\033[36m" if COLOR_ENABLED else ""
    WHITE = "\033[37m" if COLOR_ENABLED else ""

    BRIGHT_BLACK = "\033[90m" if COLOR_ENABLED else ""
    BRIGHT_RED = "\033[91m" if COLOR_ENABLED else ""
    BRIGHT_GREEN = "\033[92m" if COLOR_ENABLED else ""
    BRIGHT_YELLOW = "\033[93m" if COLOR_ENABLED else ""
    BRIGHT_BLUE = "\033[94m" if COLOR_ENABLED else ""
    BRIGHT_MAGENTA = "\033[95m" if COLOR_ENABLED else ""
    BRIGHT_CYAN = "\033[96m" if COLOR_ENABLED else ""
    BRIGHT_WHITE = "\033[97m" if COLOR_ENABLED else ""


# Semantic palette used consistently across the whole UI
PRIMARY = C.BRIGHT_CYAN
ACCENT = C.BRIGHT_MAGENTA
SUCCESS = C.BRIGHT_GREEN
WARNING = C.BRIGHT_YELLOW
ERROR = C.BRIGHT_RED
MUTED = C.BRIGHT_BLACK
LABEL = C.CYAN
VALUE = C.BOLD + C.WHITE


def style(text: str, *codes: str) -> str:
    if not COLOR_ENABLED:
        return text
    return f"{''.join(codes)}{text}{C.RESET}"


def hide_cursor():
    try:
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()
    except (ValueError, OSError):
        pass  # stream already closed (e.g. broken pipe during shutdown)


def show_cursor():
    try:
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()
    except (ValueError, OSError):
        pass  # stream already closed (e.g. broken pipe during shutdown)


def clear_line():
    sys.stdout.write("\r\033[K")
