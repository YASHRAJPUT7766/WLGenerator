"""
WL Gen main entry point.

Handles top-level dispatch: startup banner, help, version, rules list,
generate mode, random mode, and the password strength checker — with
centralized error handling that prints clean messages instead of raw
tracebacks (unless --debug is passed).
"""
from __future__ import annotations

import os
import sys

# --no-color must be applied before wlgen.ui.theme is first imported
# anywhere, since COLOR_ENABLED and the C class codes are computed once
# at import time. We check sys.argv directly, ahead of full parsing,
# so every downstream module that does `from ui.theme import ...`
# sees color already disabled.
if "--no-color" in sys.argv or os.environ.get("NO_COLOR") is not None:
    os.environ["NO_COLOR"] = "1"

from cli.flags import build_parser
from cli.help import render_help, render_version, render_rules_list
from cli import commands
from ui.banner import startup_banner
from ui.theme import C, ERROR, MUTED, style, show_cursor, hide_cursor
from utils.errors import WLGenError


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()

    try:
        args = parser.parse(argv)
    except WLGenError as exc:
        print(f"{style('Error:', ERROR)} {exc}", file=sys.stderr)
        print(style("Run 'wlgen -h' for usage.", MUTED), file=sys.stderr)
        return exc.exit_code

    debug = bool(args.get("debug"))

    try:
        return _dispatch(args, argv)
    except WLGenError as exc:
        print(f"\n{style('Error:', ERROR)} {exc}", file=sys.stderr)
        if debug:
            raise
        return exc.exit_code
    except KeyboardInterrupt:
        print(f"\n{style('Cancelled by user.', MUTED)}", file=sys.stderr)
        return 130
    except BrokenPipeError:
        # Standard Unix behavior when output is piped into a truncating
        # consumer (e.g. `wlgen -h | head`) — not a real error.
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0
    except Exception as exc:  # noqa: BLE001 - top-level safety net
        if debug:
            raise
        print(f"\n{style('Unexpected error:', ERROR)} {exc}", file=sys.stderr)
        print(style("Run with --debug for a full traceback.", MUTED), file=sys.stderr)
        return 1
    finally:
        show_cursor()


def _dispatch(args, argv: list[str]) -> int:
    if args.get("help"):
        print(render_help())
        return 0

    if args.get("version"):
        print(render_version())
        return 0

    if args.get("check"):
        commands.cmd_check(args.get("check"))
        return 0

    if args.get("rules") and not args.get("generate"):
        print(render_rules_list())
        return 0

    if args.get("random"):
        commands.cmd_random(args)
        return 0

    if args.get("generate"):
        commands.cmd_generate(args)
        return 0

    if not argv:
        print(startup_banner())
        print()
        print(style("Run 'wlgen -h' for the full command reference.", MUTED))
        return 0

    # Flags were given but none matched a recognized mode (e.g. only -o
    # without -g) — guide the user rather than silently doing nothing.
    print(style(
        "No action specified. Use -g/--generate, -r/--random, -k/--check, "
        "or -h/--help.",
        ERROR,
    ), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
