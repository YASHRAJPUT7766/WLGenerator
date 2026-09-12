# WL Gen — Wordlist Generator

<div align="center">

```
██╗    ██╗██╗          ██████╗ ███████╗███╗   ██╗
██║    ██║██║         ██╔════╝ ██╔════╝████╗  ██║
██║ █╗ ██║██║         ██║  ███╗█████╗  ██╔██╗ ██║
██║███╗██║██║         ██║   ██║██╔══╝  ██║╚██╗██║
╚███╔███╔╝███████╗    ╚██████╔╝███████╗██║ ╚████║
 ╚══╝╚══╝ ╚══════╝     ╚═════╝ ╚══════╝╚═╝  ╚═══╝
```

### ⚡ Wordlist Generator — for authorized security research

[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-brightgreen)](#license)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Kali%20%7C%20Termux-informational)](#installation)
[![Tests](https://img.shields.io/badge/tests-86%20passing-success)](#testing)
[![Status](https://img.shields.io/badge/status-active-brightgreen)](#)

*A fast, rule-based, offline wordlist generator for authorized security testing,
defensive password auditing, CTF/lab environments, and controlled local research.*

[Installation](#installation) •
[Quick start](#first-launch) •
[Examples](#examples) •
[Features](#core-concepts) •
[Kali / Termux setup](#installation)

</div>

---

WL Gen is a command-line security research utility for generating controlled,
rule-based wordlist candidates from local, user-supplied source data. It is
built for **authorized security testing, defensive password auditing,
CTF/lab environments, and controlled local research.**

> ⚠️ WL Gen does not perform authentication attempts, CAPTCHA or lockout bypass,
> credential stuffing, or attacks against remote systems. See
> [Security Boundaries](#security-boundaries) below.

### ✨ Highlights

- 🔤 **Full auto-all mode** — no flags needed, sensible defaults kick in automatically
- 🔀 **Multi-word generation** with fair, round-robin distribution across every source word
- 🔡 Case, number, symbol, and leetspeak-style rule engines — mix and match freely
- 📏 Length filtering (`min:max`), combination mode, and configurable separators
- 🧹 Case-sensitive **or** case-insensitive deduplication
- 📄 Export as plain text, **CSV**, or **JSON-lines**
- ↕️ Sortable output (by length or alphabetically)
- ⏸️ **Resume support** — safely continue an interrupted run with no duplicates
- 📊 Per-source-word statistics breakdown
- 🔐 Built-in local password strength checker



## Table of contents

- [Installation](#installation)
- [First launch](#first-launch)
- [Core concepts](#core-concepts)
- [Command reference](#command-reference)
- [Examples](#examples)
- [Configuration](#configuration)
- [Password strength checker](#password-strength-checker)
- [Performance notes](#performance-notes)
- [Troubleshooting](#troubleshooting)
- [Security boundaries](#security-boundaries)
- [Development](#development)
- [Testing](#testing)
- [Project structure](#project-structure)

---

## Installation

WL Gen requires **Python 3.11+**. It has one runtime dependency
(`colorama`, for cross-platform ANSI color support) — everything else
(TOML parsing, argument handling) uses the Python standard library.

<details open>
<summary><b>🐉 Kali Linux (or any Debian-based Linux)</b></summary>

```bash
# 1. Make sure Python 3.11+ and pip/git are available
sudo apt update
sudo apt install -y python3 python3-pip git

# 2. Clone the repository
git clone https://github.com/YASHRAJPUT7766/WLGenerator.git
cd wlgen

# 3. Install
pip install . --break-system-packages

# 4. Verify
wlgen --version
```

</details>

<details open>
<summary><b>📱 Termux (Android)</b></summary>

```bash
# 1. Update packages and install Python + git
pkg update && pkg upgrade -y
pkg install -y python git

# 2. Clone the repository
git clone https://github.com/YASHRAJPUT7766/WLGenerator.git
cd wlgen

# 3. Install
pip install . --break-system-packages

# 4. Verify
wlgen --version
```

If `git clone` isn't available or you downloaded a `.zip` instead:

```bash
pkg install -y unzip
unzip wlgen.zip
cd wlgen
pip install . --break-system-packages
```

</details>

<details>
<summary><b>🍎 macOS / 🪟 Windows (WSL)</b></summary>

```bash
git clone https://github.com/YASHRAJPUT7766/WLGenerator.git
cd wlgen
pip install .
wlgen --version
```

</details>

### Editable / development install

Use this instead of `pip install .` if you plan to modify the code —
changes take effect immediately without reinstalling:

```bash
pip install -e . --break-system-packages
```

### Verify installation

```bash
wlgen --version
```

If `wlgen` isn't found after installing, make sure your Python user
scripts directory is on your `PATH` (Termux and some Linux setups need
this) — or run it directly with `python3 -m cli.main` from the project
folder.

---

## First launch

Running `wlgen` with no arguments shows the startup interface:

```bash
$ wlgen
```

```
                    █   █ █         ████ █████ █   █
                    █   █ █        █     █     ██  █
                    █ █ █ █        █  ██ ████  █ █ █
                    █ █ █ █        █   █ █     █  ██
                     █ █  █████     ████ █████ █   █

╔════════════════════════════════════════════════════════════╗
║                                                              ║
║                      W L   G E N                            ║
║                  WORDLIST GENERATOR                         ║
║                                                              ║
║                Security Research Utility                    ║
║                                                              ║
╚════════════════════════════════════════════════════════════╝
Controlled  ·  Offline  ·  Rule-based  ·  Authorized use only
                            v3.2.1

Run 'wlgen -h' for the full command reference.
```

From there:

```bash
wlgen -h                          # full categorized help
wlgen -g -wd Yash                # generate from a single word
wlgen -g -wd Yash -n 10000 -o result.txt
```

---

## Core concepts

WL Gen has three independent modes, selected by their own top-level flag:

| Mode | Flag | Purpose |
|---|---|---|
| **Generate** | `-g` / `--generate` | Deterministic, rule-based wordlist generation from source words |
| **Random**   | `-r` / `--random`   | Controlled random test-data generation (not word-based) |
| **Check**    | `-k` / `--check`    | Local password strength analysis |

These modes are mutually exclusive in a single invocation — run them
separately.

### Generate mode

Generate mode takes one or more **source words** (from `-wd`/`--word`
and/or an existing wordlist file via `-w`/`--wordlist`) and expands them
through a set of **rule categories**: case transforms, prefixes,
suffixes, numbers, symbols, separators, controlled leetspeak
substitutions, and pairwise word combinations. The result is
deterministic — the same input words and the same rules always produce
the same candidate set.

**If you don't specify any rule flags, every category is enabled
automatically** (`--all`), auto-scaled to the requested count — so
`wlgen -g -wd Yash -n 10000` alone produces a real mixed set (case
variants, numbers, symbols, leet substitutions) without you having to
pick anything. See [Automatic "use everything" mode](#automatic-use-everything-mode-default)
below. The moment you specify any rule flag yourself (`-c`, `-N`, `-S`,
`-p`, `-s`, `-x`, `--leet`, `--combine`, `--no-dedupe`, or `--config`),
WL Gen switches to using exactly what you specified instead.

### Random mode

Random mode is a **separate, clearly distinct** generator that produces
cryptographically random strings from a configurable character set and
length. It does not use word-based rules and is not mixed with
deterministic generation in the same run.

### Automatic "use everything" mode (default)

Give a word and a count, get a comprehensive result — no need to pick
rules by hand:

```bash
wlgen -g -wd Yash -n 10000 -o result.txt
```

This alone enables case (`lower`, `upper`, `capitalize`, `title`),
a number range, symbols, and leet-style substitutions together,
producing a genuinely mixed set (`yash`, `YASH`, `Yash!`, `y@sh42`,
`yash9981`, ...) rather than one flavor at a time. `--all` makes this
explicit if you want to say so in a script, but it changes nothing —
no flags and `--all` behave identically.

The number range widens automatically with the requested count, so a
bigger `-n` gets a wider space to draw from instead of running out:

| Requested count      | Number range used |
|---|---|
| up to 1,000           | 0–99 |
| up to 100,000          | 0–9,999 |
| up to 5,000,000        | 0–99,999 |
| above 5,000,000        | 0–999,999 |

With two or more source words and a requested count over 10,000,
`--combine` (pairwise word concatenation) is also switched on
automatically.

As soon as you pass any specific rule flag — `-c`, `-N`, `-S`, `-p`,
`-s`, `-x`, `--leet`, `--combine`, `--no-dedupe`, or `--config` — WL Gen
uses exactly what you asked for instead of the automatic set:

```bash
# Only lowercase, nothing else -- because -c was given explicitly
wlgen -g -wd Yash -c lower -n 1000 -o result.txt
```

### Requested vs. possible

You control output size with `-n`/`--count`. If your rule set can only
produce fewer unique candidates than requested, WL Gen tells you plainly
instead of silently duplicating entries to pad the file:

```
Requested      : 1,000,000
Possible       :   742,300
Generated      :   742,300
Duplicates     :         0
```

There is no way around this — a fixed word plus a fixed, finite set of
rules only has so many unique combinations. To reach a bigger requested
count, enable more rule categories (more case modes, more numbers,
symbols, prefixes/suffixes, `--leet`, `--combine`, more source words)
so there's a larger space for WL Gen to draw from.

### Automatic number ranges (no need to type every number)

Typing out `-N 1,2,3,4,5,...,9999` by hand isn't necessary. `-N`/`--numbers`
accepts `range:START-END` (and `range:START-END:STEP`), which expands to
every value in that range automatically:

```bash
# Same as manually listing 0,1,2,...,9999 -- but automatic
wlgen -g -wd Yash -N range:0-9999 -n 10000 -o result.txt
```

WL Gen walks through the range in order (`yash`, `yash0`, `yash1`, ...,
`yash9999`) and stops as soon as it has produced the requested count —
so if you ask for exactly `-n 10000`, it may not need the full range to
satisfy the request. Explicit values and ranges can be mixed in the same
flag (`-N 1,12,range:2000-2025`), and `--pad` zero-pads a range to a
fixed width for PIN-style output (`00`, `01`, ... `99` instead of `0`,
`1`, ... `99`).

A range is capped at 1,000,000 expanded values as a safety limit (to
stop an accidental `range:0-999999999` from trying to build a
billion-entry list before generation even starts) — use a `:STEP` to
cover a wider span within that limit, e.g. `range:0-9999999:10`.

---

## Command reference

Run `wlgen -h` at any time for the live, categorized version of this
table (grouped exactly as below, with usage examples).

### INPUT OPTIONS

| Short | Long | Description |
|---|---|---|
| `-w`  | `--wordlist` | Use an existing local wordlist file as input |
| `-wd` | `--word`     | Provide a custom source word (repeatable: `-wd A -wd B`) |
|       | `--encoding` | Text encoding for reading input files (default: `utf-8`) |

### GENERATION OPTIONS

| Short | Long | Description |
|---|---|---|
| `-g` | `--generate` | Start deterministic generation |
| `-n` | `--count`    | Requested number of generated candidates |
| `-r` | `--random`   | Enable controlled random test-data mode |
|      | `--charset`  | Character set for random mode: `alnum`, `alpha`, `lower`, `upper`, `digits`, `full`, or a custom string |
| `-l` | `--length`   | Random mode: fixed length. Word mode: length filter (`N` or `MIN:MAX`) |
|      | `--combine`  | Combine pairs of supplied source words |
|      | `--all`      | Enable every rule category, auto-scaled to `-n` (this is the default when no other rule flag is given) |

### TRANSFORMATION OPTIONS

| Short | Long | Description |
|---|---|---|
| `-p` | `--prefix`     | Add a prefix (repeatable) |
| `-s` | `--suffix`     | Add a suffix (repeatable) |
| `-N` | `--numbers`    | Numeric suffixes: comma list (`1,123,2025`) and/or `range:START-END` |
| `--pad` |             | Zero-pad numbers from a range to a fixed width (`00`..`99` instead of `0`..`99`) |
| `-S` | `--symbols`    | Comma-separated symbol suffixes, e.g. `!,@,#` |
| `-c` | `--case`       | Comma-separated case modes: `lower,upper,capitalize,title` |
| `-x` | `--separator`  | Comma-separated separators joining prefix/word/suffix segments |
|      | `--leet`       | Enable controlled leetspeak-style substitutions |
| `-d` | `--deduplicate`| Remove duplicate candidates (on by default) |
|      | `--no-dedupe`  | Disable deduplication |
|      | `--dedupe-ci`  | Deduplicate case-insensitively (`Yash1` and `YASH1` count as one) |

### OUTPUT OPTIONS

| Short | Long | Description |
|---|---|---|
| `-o` | `--output` | Output file path |
| `-f` | `--force`  | Overwrite output file without prompting |
|      | `--json`   | Write machine-readable JSON statistics to a file |
|      | `--format` | Output file format: `txt` (default), `csv`, or `jsonl`. Inferred from `-o`'s extension if not given |
|      | `--sort`   | Sort output: `length-asc`, `length-desc`, or `alpha` (default: unsorted/streamed) |
|      | `--resume` | Resume an interrupted run, appending to the existing output file |

### DISPLAY OPTIONS

| Short | Long | Description |
|---|---|---|
| `-P` | `--preview`   | Preview the result without writing full output |
|      | `--stats`     | Display detailed generation statistics |
|      | `--dry-run`   | Calculate the generation plan without writing the file |
| `-q` | `--quiet`     | Suppress non-essential output |
|      | `--no-color`  | Disable colored output |
| `-y` | `--yes`       | Automatically confirm large-operation prompts |

### CONFIGURATION OPTIONS

| Short | Long | Description |
|---|---|---|
| | `--config` | Load a custom TOML configuration file |
| | `--rules`  | Display available generation rule categories |

### UTILITY OPTIONS

| Short | Long | Description |
|---|---|---|
| `-k` | `--check`   | Analyze the strength of a local password string |
|      | `--version` | Display the current version |
| `-h` | `--help`    | Display complete help |
|      | `--debug`   | Show full tracebacks on error |

Both `--flag value` and `--flag=value` syntax are accepted. Flags combine
freely in any order.

---

## Examples

```bash
# Show the startup interface
wlgen

# Generate from a single word (defaults: lowercase, count 1000, wordlist.txt)
wlgen -g -wd Yash

# Generate from multiple words
wlgen -g -wd Yash -wd Kumar

# Generate from an existing wordlist file
wlgen -g -w words.txt

# Combine a wordlist file with extra custom words
wlgen -g -w words.txt -wd Yash

# Generate 100,000 candidates to a named output file
wlgen -g -wd Yash -n 100000 -o result.txt

# Preview without writing the full file
wlgen -g -wd Yash -P

# See the generation plan only, without creating the output
wlgen -g -wd Yash -n 1000000 --dry-run

# Custom case rules, numeric suffixes, symbol suffixes, separators
wlgen -g -wd Yash -c lower,capitalize -N 1,123,2025 -S '!,@,#' -x ',_'

# Auto-try every number from 0 to 9999 as a suffix -- no need to list
# each one by hand. If you ask for -n 10000, WL Gen tries the range in
# order until the requested count is reached.
wlgen -g -wd Yash -N range:0-9999 -n 10000 -o result.txt

# Zero-padded PIN-style range: yash00, yash01, ... yash99
wlgen -g -wd Yash -N range:0-99 --pad -n 100 -o pins.txt

# Step through a range in increments (range:START-END:STEP)
wlgen -g -wd Yash -N range:0-1000:10

# Mix explicit values with a range in the same flag
wlgen -g -wd Yash -N 1,12,range:2000-2025

# Combine two source words pairwise (e.g. "yashkumar", "kumaryash")
wlgen -g -wd Yash -wd Kumar --combine

# Enable controlled leetspeak-style substitutions
wlgen -g -wd Yash --leet

# Random mode: 5,000 twelve-character strings
wlgen -r -l 12 -n 5000 -o random.txt

# Check local password strength
wlgen -k 'Summer2024!'

# Generate using a saved configuration file
wlgen -g -wd Yash --config myconfig.toml

# Machine-readable statistics for scripting/CI
wlgen -g -wd Yash -n 5000 -o out.txt -y --json stats.json

# Non-interactive / scripted runs (skip all prompts)
wlgen -g -wd Yash -n 500000 -o out.txt -y -f -q

# Multiple source words, capped at 6 characters each, output only
wlgen -g -wd John -wd Doe -l :6 -n 500 -o result.txt

# Case-insensitive dedupe -- "Yash1" and "YASH1" count as one
wlgen -g -wd Yash --dedupe-ci -n 1000 -o result.txt

# Export as CSV or JSON-lines instead of plain text (auto-detected
# from the output extension, or force it with --format)
wlgen -g -wd Yash -n 1000 -o result.csv
wlgen -g -wd Yash -n 1000 -o result.jsonl
wlgen -g -wd Yash -n 1000 -o result.txt --format csv

# Sort the output by length or alphabetically (materializes the full
# set in memory to sort, instead of the usual constant-memory stream)
wlgen -g -wd Yash -n 1000 -o sorted.txt --sort length-asc

# See how many candidates each source word contributed
wlgen -g -wd Yash -wd Kumar -n 1000 -o out.txt --stats

# If a large run gets interrupted (Ctrl+C), re-run the exact same
# command with --resume to continue from where it left off, appending
# to the existing output file without duplicating anything already
# written
wlgen -g -wd Yash -n 5000000 -o big.txt
# ...interrupted partway through...
wlgen -g -wd Yash -n 5000000 -o big.txt --resume
```

---

## Configuration

Advanced users can define reusable rule sets in a TOML file instead of
passing everything via flags:

```toml
# config.toml
[generation]
case = ["lower", "capitalize"]
prefixes = []
suffixes = ["Team", "2025"]
numbers = ["1", "12", "123", "2024", "2025"]
symbols = ["!", "@", "#"]
separators = ["", "_"]
substitutions = false
combine_words = false
min_length = 6
max_length = 20

[output]
deduplicate = true
```

Load it with:

```bash
wlgen -g -wd Yash --config config.toml
```

Configuration is validated before generation starts — invalid case
modes, wrong types, or an impossible `min_length`/`max_length` range are
rejected with a clear error rather than failing partway through a run.

**Precedence:** explicit CLI flags override values from the config file,
which override built-in defaults. This lets you keep a base config and
override just one or two rules per run.

An example file is included at `config/example_config.toml`.

---

## Password strength checker

```bash
wlgen -k 'YourPasswordHere'
```

This performs a **purely local, offline** analysis. Nothing is
transmitted, logged externally, or stored. It reports:

- length and character-set diversity
- estimated entropy (bits)
- repeated-character and repeated-block detection
- sequential-pattern detection (`abc`, `123`, `qwerty`, etc.)
- matches against a small set of well-known weak passwords and weak
  "dictionary word + digits" constructions
- an illustrative offline guessing-time estimate
- an overall verdict: Very Weak / Weak / Moderate / Strong / Very Strong

This is a heuristic estimator for awareness and defensive auditing, not
a cryptographic guarantee, and it is not connected to any authentication
system, live or otherwise.

---

## Performance notes

- **Streaming generation.** Candidates are produced and written lazily;
  WL Gen does not hold the full generated dataset in memory.
- **Buffered I/O.** Output is written through a buffered stream rather
  than line-by-line syscalls.
- **Bounded deduplication.** Deduplication uses a set of the generated
  strings themselves. For very large rule spaces this is the standard
  memory/exactness tradeoff — candidates are typically short, so memory
  overhead per entry is modest, but extremely large unique spaces will
  scale memory roughly linearly with unique output size.
- **Fast estimation.** Preview and `--dry-run` use sampling to estimate
  the candidate space quickly rather than fully enumerating it up front;
  the actual generation run always reports exact final counts.
- **Large-operation confirmation.** Requests above an internal threshold
  show an estimate of output size and ask for confirmation before
  proceeding. Use `-y`/`--yes` to skip this in scripts, or `-f`/`--force`
  to skip the separate "file already exists" prompt.
- **Non-interactive safety.** If stdin is not an interactive terminal,
  WL Gen never blocks waiting for a prompt response — it treats an
  unanswerable prompt as "no" and tells you which flag to pass instead
  (`-y` or `-f`). This matters when running WL Gen from scripts, CI, or
  with redirected input.
- **Ctrl+C handling.** Interrupting a generation run stops cleanly,
  keeps the partial output already written to disk, and reports it was
  interrupted rather than crashing.

---

## Troubleshooting

**"Wordlist file not found"**
Check the path passed to `-w`/`--wordlist`. Relative paths are resolved
from your current working directory.

**"No source words provided"**
Generate mode needs at least one source word via `-wd`/`--word` and/or
an existing file via `-w`/`--wordlist`.

**"Unsupported encoding" / decode errors reading a wordlist**
Pass the correct encoding explicitly, e.g. `--encoding latin-1`.

**"Insufficient disk space"**
WL Gen estimates output size before writing and checks free disk space
with a safety margin. Free up space or reduce `-n`.

**"Output directory does not exist" / permission errors**
Make sure the target directory exists and is writable. WL Gen checks
this before starting generation rather than failing partway through.

**A generate/random run seems to hang**
It doesn't — if you see a confirmation prompt with no visible response,
you're most likely running WL Gen non-interactively (stdin isn't a
terminal). Re-run with `-y` (confirm large operations) and/or `-f`
(overwrite existing output) to skip prompts entirely.

**Fewer candidates were generated than requested**
This is expected behavior, not an error: WL Gen never duplicates entries
to reach a requested count. Enable more rule categories (case modes,
numbers, symbols, prefixes/suffixes, `--leet`, `--combine`) to expand
the candidate space, or lower `-n`.

**Raw Python traceback**
This should never happen during normal use — WL Gen catches its own
error types and prints a clean message. If you do see one, please open
an issue with the exact command you ran. You can reproduce with
`--debug` to get the full traceback for a bug report.

---

## Security boundaries

WL Gen is scoped intentionally narrowly. It:

- operates only on **local, user-provided** data (words you type, or a
  wordlist file you already have)
- performs **no network requests** of any kind
- does **not** implement CAPTCHA bypass, authentication bypass,
  account-lockout bypass, credential stuffing, automated login attempts,
  or any mechanism for attacking remote systems or accounts
- does **not** transmit, log, or store anything you check with the
  password strength analyzer

If you're looking for a tool to test authentication endpoints, rate
limits, or lockout policies against a system you're authorized to test,
that is a different category of tool with its own authorization and
scoping requirements — WL Gen intentionally does not do this.

Use WL Gen only against data and systems you own or are explicitly
authorized to test.

---

## Development

Every top-level folder (`cli/`, `rules/`, `generator/`, etc.) is its own
Python package at the repo root — see [Project structure](#project-structure)
below. Notable design choices:

- **No `argparse`/`click` for the main parser.** WL Gen's short-flag
  design (`-wd` as a repeatable two-character flag alongside
  single-character flags like `-g`, with flags combining in any order)
  doesn't map cleanly onto argparse's or click's single-dash clustering
  model, so `cli/parser.py` implements a small, explicit parser
  instead. Every flag is registered with its arity (`FLAG`, `VALUE`, or
  `REPEATED`) up front.
- **Zero heavyweight UI dependency.** Terminal styling uses raw ANSI
  escape codes (`ui/theme.py`) plus `colorama` for cross-platform
  compatibility, rather than a larger TUI framework — keeping install
  size and dependency surface minimal.
- **`tomllib` for config**, from the standard library (Python 3.11+),
  so no extra TOML dependency is needed.

To set up a development environment:

```bash
git clone https://github.com/YASHRAJPUT7766/WLGenerator.git
cd wlgen
pip install -e ".[dev]"
```

### Adding a new rule category

1. Add the transformation function to `rules/definitions.py`.
2. Wire it into `RuleSet` (fields + `enabled_categories()`).
3. Apply it in `rules/engine.py::build_variant_pool`.
4. Add the corresponding CLI flag in `cli/flags.py` and resolve it
   in `cli/resolve.py::resolve_ruleset`.
5. Document it in `--rules` output (`cli/help.py::render_rules_list`)
   and in this README.

---

## Testing

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Or, with `pytest` installed (`pip install -e ".[dev]"`):

```bash
pytest tests -v
```

The test suite covers:

- rule transformations (case, numbers, symbols, length filters, word
  combination)
- the streaming/deduplicating generation engine, including exact
  candidate-space exhaustion and requested-count limiting
- the CLI argument parser (combined flags, repeated flags, inline
  `--flag=value` syntax, error cases)
- the password strength checker across weak, dictionary-pattern, and
  strong passwords

---

## Project structure

```
wlgen/                (repository root — clone lands here)
├── cli/          CLI parsing, flag definitions, help screen, dispatch
├── generator/    Core streaming generation engine + random mode + resume
├── rules/        Rule definitions and the transformation pipeline
├── input/        Source word collection (CLI words + wordlist files)
├── output/       Streaming file writer (txt/csv/jsonl) + statistics/JSON export
├── checker/      Local password strength analysis
├── config/       TOML configuration loading and validation
├── ui/           Terminal theme, banner, progress bar
├── utils/        Errors, formatting, disk/system helpers
├── _meta/        Package version and app name
├── tests/        Unit tests (86 tests)
├── pyproject.toml
├── README.md
└── LICENSE
```

Every top-level folder here is an independent Python package — there is
no single `wlgen/` package wrapper inside the repo, so `cli`, `rules`,
etc. are imported directly (e.g. `from cli.main import main`).

---

## License

MIT. See the `license` field in `pyproject.toml`; add a `LICENSE` file
with the full text before distributing if you require one.
