"""
Resolves parsed CLI arguments (optionally layered over a loaded config
file) into a validated RuleSet and other run parameters.

Precedence: explicit CLI flags override config file values, which
override built-in defaults.
"""
from __future__ import annotations

from cli.parser import ParsedArgs
from config.loader import AppConfig, VALID_CASE_MODES
from rules.definitions import RuleSet, DEFAULT_SEPARATORS, DEFAULT_NUMBERS, DEFAULT_SYMBOLS
from utils.errors import ArgumentError

# Safety ceiling for a single range: expr like "range:0-99999999" would
# otherwise silently try to build a hundred-million-entry list in memory
# before generation even starts. This keeps range expansion itself bounded;
# the overall candidate space is still governed by -n/--count on top of this.
MAX_RANGE_SIZE = 1_000_000


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip() != ""]


def _expand_range_token(token: str, flag_name: str, zero_pad: bool = False) -> list[str]:
    """
    Expand a single 'range:START-END' or 'range:START-END:STEP' token into
    every value in that range, so the user doesn't have to type each one.

    'range:0-9999' -> ['0', '1', '2', ..., '9999']
    'range:2000-2025' -> ['2000', '2001', ..., '2025']
    'range:0-100:5' -> ['0', '5', '10', ..., '100']

    zero_pad=True keeps common widths padded (e.g. '00'..'99' instead of
    '0'..'99'), which matters for PIN-style suffixes.
    """
    body = token[len("range:"):]
    parts = body.split(":")
    if len(parts) not in (1, 2):
        raise ArgumentError(
            f"Invalid range syntax in {flag_name}: '{token}'. "
            f"Use 'range:START-END' or 'range:START-END:STEP'."
        )
    bounds = parts[0]
    step = int(parts[1]) if len(parts) == 2 else 1
    if step <= 0:
        raise ArgumentError(f"Invalid range step in {flag_name}: '{token}' (step must be positive).")

    if "-" not in bounds:
        raise ArgumentError(
            f"Invalid range syntax in {flag_name}: '{token}'. "
            f"Expected 'START-END', e.g. 'range:0-9999'."
        )
    start_s, _, end_s = bounds.rpartition("-")
    if not start_s or not start_s.isdigit() or not end_s.isdigit():
        raise ArgumentError(
            f"Invalid range bounds in {flag_name}: '{token}'. "
            f"Expected exactly two non-negative integers separated by one "
            f"'-', e.g. 'range:0-9999'."
        )
    start, end = int(start_s), int(end_s)
    if start > end:
        raise ArgumentError(f"Invalid range in {flag_name}: '{token}' — START cannot exceed END.")

    size = (end - start) // step + 1
    if size > MAX_RANGE_SIZE:
        raise ArgumentError(
            f"Range in {flag_name} ('{token}') expands to {size:,} values, which "
            f"exceeds the safety limit of {MAX_RANGE_SIZE:,}. Narrow the range or "
            f"increase the step, e.g. 'range:{start}-{end}:10'."
        )

    width = len(end_s) if zero_pad else 0
    return [str(n).zfill(width) for n in range(start, end + 1, step)]


def _split_csv_with_ranges(value: str | None, flag_name: str, zero_pad: bool = False) -> list[str]:
    """
    Like _split_csv, but any comma-separated token of the form
    'range:START-END' or 'range:START-END:STEP' is expanded into every
    value in that range. Plain tokens pass through unchanged, so ranges
    and explicit values can be mixed freely:

    '-N 1,12,range:2000-2025'  ->  1, 12, 2000, 2001, ..., 2025
    """
    if not value:
        return []
    out: list[str] = []
    for token in [v.strip() for v in value.split(",") if v.strip() != ""]:
        if token.lower().startswith("range:"):
            out.extend(_expand_range_token(token, flag_name, zero_pad=zero_pad))
        else:
            out.append(token)
    return out


def parse_length_option(value: str | None, random_mode: bool):
    """
    -l / --length is overloaded:
      - in random mode: a single integer length
      - in word mode: an optional 'min:max' length filter
    Returns (single_length_or_None, (min_len, max_len)_or_(None, None))
    """
    if value is None:
        return None, (None, None)

    if random_mode:
        if not value.isdigit():
            raise ArgumentError(f"--length must be a positive integer in random mode, got '{value}'.")
        n = int(value)
        if n <= 0:
            raise ArgumentError("--length must be greater than zero.")
        return n, (None, None)

    if ":" in value:
        min_s, _, max_s = value.partition(":")
        min_len = int(min_s) if min_s else None
        max_len = int(max_s) if max_s else None
        if min_len is not None and min_len < 0:
            raise ArgumentError("--length min value cannot be negative.")
        if max_len is not None and max_len < 0:
            raise ArgumentError("--length max value cannot be negative.")
        if min_len is not None and max_len is not None and min_len > max_len:
            raise ArgumentError("--length min value cannot exceed max value.")
        return None, (min_len, max_len)

    if not value.isdigit():
        raise ArgumentError(f"Invalid --length value: '{value}'.")
    n = int(value)
    return None, (n, n)


def parse_count(value: str | None) -> int | None:
    if value is None:
        return None
    cleaned = value.replace(",", "").replace("_", "")
    if not cleaned.isdigit():
        raise ArgumentError(f"--count must be a positive integer, got '{value}'.")
    n = int(cleaned)
    if n <= 0:
        raise ArgumentError("--count must be greater than zero.")
    return n


def validate_case_modes(modes: list[str]):
    for mode in modes:
        if mode not in VALID_CASE_MODES:
            raise ArgumentError(
                f"Invalid case mode '{mode}'. Valid options: "
                f"{', '.join(sorted(VALID_CASE_MODES))}."
            )


# Rule flags that, if the user supplies any one of them, mean "the user
# is hand-picking rules" -- so --all / the auto-all default should NOT
# override their choices. Deliberately excludes count/output/display
# flags, which are orthogonal to which transformation rules apply.
_EXPLICIT_RULE_FLAGS = (
    "case", "prefix", "suffix", "numbers", "symbols", "separator",
    "substitutions", "combine", "no_deduplicate",
)


def _user_picked_explicit_rules(args: ParsedArgs) -> bool:
    return any(args.get(name) for name in _EXPLICIT_RULE_FLAGS)


def _auto_all_ruleset(word_count: int, requested: int) -> RuleSet:
    """
    Build a comprehensive RuleSet that enables every category at once,
    auto-scaled so the candidate space comfortably covers the requested
    count. This is what runs by default when the user gives no explicit
    rule flags (or when they pass --all explicitly), so 'just generate
    N from this word' produces a real mixed set of case/number/symbol/
    leet/combine variants rather than only one flavor.

    Scaling logic: start from a modest, always-on baseline (this alone
    covers small requests like -n 100 without needless bloat), then
    widen the number range and symbol set, and switch on --combine, as
    the requested count grows -- so a request for 10,000,000 automatically
    gets a wide enough space instead of silently capping out.
    """
    case_modes = ["lower", "upper", "capitalize", "title"]
    symbols = ["!", "@", "#", "$", "*", "_", "."]

    if requested <= 1_000:
        number_range_end = 99
    elif requested <= 100_000:
        number_range_end = 9_999
    elif requested <= 5_000_000:
        number_range_end = 99_999
    else:
        number_range_end = 999_999

    numbers = [str(n) for n in range(0, number_range_end + 1)]

    return RuleSet(
        case_modes=case_modes,
        numbers=numbers,
        symbols=symbols,
        separators=[""],
        use_substitutions=True,
        combine_words=word_count >= 2 and requested > 10_000,
        deduplicate=True,
    )


def resolve_ruleset(args: ParsedArgs, config: AppConfig | None,
                     word_count: int = 1, requested: int = 1000) -> RuleSet:
    """Build the effective RuleSet from config (if any) + CLI overrides.

    If the user gave no explicit rule flags (and no config file), and
    didn't ask for random mode, "all rules, auto-scaled to fit -n" is
    the default -- --all makes that explicit but changes nothing.
    """
    use_auto_all = (
        config is None
        and not _user_picked_explicit_rules(args)
    )

    if use_auto_all:
        rs = _auto_all_ruleset(word_count=word_count, requested=requested)
    elif config:
        rs = config.to_ruleset()
    else:
        # The user hand-picked at least one rule flag (e.g. just -c lower).
        # Only the category/categories they actually named should be
        # narrowed -- everything they *didn't* mention should keep a
        # sane baseline instead of silently going empty/off. Start from
        # the same defaults DEFAULT_* already define (previously unused),
        # and let the per-flag overrides below replace whichever of
        # these the user actually specified.
        rs = RuleSet(
            case_modes=["lower"],
            numbers=list(DEFAULT_NUMBERS),
            symbols=list(DEFAULT_SYMBOLS),
        )

    if args.get("case") is not None:
        modes = _split_csv(args.get("case"))
        validate_case_modes(modes)
        rs.case_modes = modes

    if args.get("prefix"):
        rs.prefixes = list(args.get("prefix"))

    if args.get("suffix"):
        rs.suffixes = list(args.get("suffix"))

    if args.get("numbers") is not None:
        rs.numbers = _split_csv_with_ranges(
            args.get("numbers"), "-N/--numbers", zero_pad=bool(args.get("pad_numbers"))
        )

    if args.get("symbols") is not None:
        rs.symbols = _split_csv(args.get("symbols"))

    if args.get("separator") is not None:
        seps = _split_csv(args.get("separator"))
        rs.separators = seps if seps else list(DEFAULT_SEPARATORS)

    if args.get("substitutions"):
        rs.use_substitutions = True

    if args.get("combine"):
        rs.combine_words = True

    if args.get("no_deduplicate"):
        rs.deduplicate = False
    elif args.get("deduplicate"):
        rs.deduplicate = True

    if args.get("dedupe_ci"):
        rs.dedupe_case_insensitive = True

    _, (min_len, max_len) = parse_length_option(args.get("length"), random_mode=False)
    if min_len is not None:
        rs.min_length = min_len
    if max_len is not None:
        rs.max_length = max_len

    if not rs.case_modes:
        rs.case_modes = ["lower"]

    return rs


def check_flag_compatibility(args: ParsedArgs):
    """Reject explicitly incompatible flag combinations early with clear errors."""
    if args.get("random") and args.get("generate"):
        random_specific = any([
            args.get("charset"),
        ])
        word_specific = any([
            args.get("word"), args.get("wordlist"), args.get("prefix"),
            args.get("suffix"), args.get("numbers"), args.get("symbols"),
            args.get("substitutions"), args.get("combine"), args.get("all_rules"),
        ])
        if word_specific and random_specific:
            raise ArgumentError(
                "Random mode (-r) cannot be combined with deterministic word "
                "rules and a random charset in the same run. Run them separately, "
                "or drop the word-specific flags to use random mode alone."
            )
        if word_specific:
            raise ArgumentError(
                "Random mode (-r) does not use word-based rules (-wd, -w, -p, -s, "
                "-N, -S, --leet, --combine). Remove them or drop -r."
            )

    if args.get("preview") and args.get("dry_run"):
        raise ArgumentError("Use either --preview (-P) or --dry-run, not both.")

    if args.get("wordlist") and not args.get("generate") and not args.get("random"):
        pass  # harmless; generate/random gating handled by caller

    if args.get("check") and (args.get("generate") or args.get("random")):
        raise ArgumentError(
            "-k/--check (password strength) cannot be combined with -g or -r "
            "in the same invocation. Run it separately."
        )
