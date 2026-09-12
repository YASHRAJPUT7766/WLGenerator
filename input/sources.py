"""
Input sourcing.

Collects seed words from two possible sources:
  - custom words supplied directly on the command line (-wd / --word,
    repeatable)
  - an existing local wordlist file (-w / --wordlist)

Both may be combined. Order is preserved; duplicates are stripped
while keeping first occurrence order.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from utils.errors import InputFileError

MAX_WORDLIST_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB sanity ceiling for a "word source"


@dataclass
class SeedWords:
    words: list[str] = field(default_factory=list)
    from_file: int = 0
    from_cli: int = 0
    source_file: str | None = None

    @property
    def count(self) -> int:
        return len(self.words)


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def load_wordlist_file(path: str, encoding: str = "utf-8") -> list[str]:
    """Read a newline-delimited wordlist file, returning stripped non-empty lines."""
    if not os.path.exists(path):
        raise InputFileError(f"Wordlist file not found: '{path}'")
    if not os.path.isfile(path):
        raise InputFileError(f"Wordlist path is not a file: '{path}'")
    if not os.access(path, os.R_OK):
        raise InputFileError(f"No read permission for wordlist file: '{path}'")

    size = os.path.getsize(path)
    if size > MAX_WORDLIST_BYTES:
        from utils.formatting import human_size
        raise InputFileError(
            f"Wordlist file too large to load as a word source "
            f"({human_size(size)} > {human_size(MAX_WORDLIST_BYTES)})."
        )

    try:
        with open(path, "r", encoding=encoding, errors="strict") as f:
            lines = [line.strip() for line in f]
    except UnicodeDecodeError as exc:
        raise InputFileError(
            f"Unsupported encoding while reading '{path}' as {encoding}: {exc}. "
            f"Try a different --encoding value."
        )
    except OSError as exc:
        raise InputFileError(f"Could not read wordlist file '{path}': {exc}")

    return [line for line in lines if line]


def collect_seed_words(
    cli_words: list[str] | None,
    wordlist_path: str | None,
    encoding: str = "utf-8",
) -> SeedWords:
    """Combine CLI-supplied words and/or a wordlist file into one seed set."""
    cli_words = cli_words or []
    combined: list[str] = []
    from_file_count = 0

    if wordlist_path:
        file_words = load_wordlist_file(wordlist_path, encoding=encoding)
        from_file_count = len(file_words)
        combined.extend(file_words)

    combined.extend(cli_words)

    if not combined:
        raise InputFileError(
            "No source words provided. Use -wd/--word to supply a word, "
            "or -w/--wordlist to load an existing wordlist file."
        )

    deduped = _dedupe_preserve_order(combined)

    return SeedWords(
        words=deduped,
        from_file=from_file_count,
        from_cli=len(cli_words),
        source_file=wordlist_path,
    )
