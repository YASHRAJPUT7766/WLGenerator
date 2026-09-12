"""
Buffered streaming output writer.

Writes candidates to disk incrementally rather than holding the full
generated set in memory, and reports running byte counts for progress
display. Supports plain-text (one candidate per line, the default),
CSV, and JSON-lines output formats.
"""
from __future__ import annotations

import csv
import json
from typing import Callable, Iterator, Literal

from utils.errors import OutputError
from utils.system import ensure_writable_path

DEFAULT_BUFFER_SIZE = 1024 * 1024  # 1 MB write buffer
OutputFormat = Literal["txt", "csv", "jsonl"]
VALID_OUTPUT_FORMATS = ("txt", "csv", "jsonl")


class WriteInterrupted(KeyboardInterrupt):
    """
    Raised instead of a plain KeyboardInterrupt when generation is
    cancelled mid-write, carrying the exact number of candidates (and
    bytes) that were actually flushed to disk before the interrupt --
    which can differ from how many the upstream generator had already
    produced. Callers that care only about "was this interrupted" can
    still catch KeyboardInterrupt as before; callers that need the
    precise on-disk count (e.g. --resume) should catch this subclass
    and read .written_count / .written_bytes.
    """

    def __init__(self, written_count: int, written_bytes: int):
        super().__init__()
        self.written_count = written_count
        self.written_bytes = written_bytes


def write_stream_to_file(
    candidates: Iterator[str],
    output_path: str,
    encoding: str = "utf-8",
    progress_callback: Callable[[int, int], None] | None = None,
    report_every: int = 500,
    output_format: OutputFormat = "txt",
    append: bool = False,
) -> tuple[int, int]:
    """
    Consume `candidates` and write to `output_path` in the requested
    format:
      - "txt"   (default): one candidate per line, exactly as before
      - "csv"   : a single "candidate" column, one row per candidate
      - "jsonl" : one JSON object per line, {"candidate": "..."}

    `append=True` opens the file in append mode instead of truncating it
    -- used by --resume to continue an interrupted run without rewriting
    (or re-including the header of) what was already written. In append
    mode with output_format="csv", the header row is skipped since it's
    already present from the original run.

    Returns (total_written, total_bytes).
    Calls progress_callback(count, bytes_written) every `report_every`
    lines if provided.
    """
    ensure_writable_path(output_path)

    total_written = 0
    total_bytes = 0
    mode = "a" if append else "w"

    try:
        with open(output_path, mode, encoding=encoding, buffering=DEFAULT_BUFFER_SIZE,
                  newline="" if output_format == "csv" else "\n") as f:
            csv_writer = None
            if output_format == "csv":
                csv_writer = csv.writer(f)
                if not append:
                    csv_writer.writerow(["candidate"])

            try:
                for candidate in candidates:
                    if output_format == "csv":
                        start_pos = f.tell()
                        csv_writer.writerow([candidate])
                        total_bytes += f.tell() - start_pos
                    elif output_format == "jsonl":
                        line = json.dumps({"candidate": candidate}) + "\n"
                        f.write(line)
                        total_bytes += len(line.encode(encoding, errors="replace"))
                    else:
                        line = candidate + "\n"
                        f.write(line)
                        total_bytes += len(line.encode(encoding, errors="replace"))

                    total_written += 1
                    if progress_callback and total_written % report_every == 0:
                        progress_callback(total_written, total_bytes)
            except KeyboardInterrupt:
                # Make sure everything written so far is actually flushed to
                # disk before we report the count back to the caller -- the
                # caller (see cli.commands) uses total_written to record
                # --resume state, which must match what's really on disk,
                # not what the generator merely produced upstream of us.
                f.flush()
                if progress_callback:
                    progress_callback(total_written, total_bytes)
                raise WriteInterrupted(total_written, total_bytes)

            if progress_callback:
                progress_callback(total_written, total_bytes)
    except PermissionError as exc:
        raise OutputError(f"Permission denied writing to '{output_path}': {exc}")
    except OSError as exc:
        if getattr(exc, "errno", None) == 28:  # ENOSPC
            raise OutputError(f"Disk full while writing '{output_path}'.")
        raise OutputError(f"Error writing to '{output_path}': {exc}")

    return total_written, total_bytes


def estimate_output_bytes(sample_candidates: list[str], total_count: int) -> int:
    """Estimate total output file size from a sample of candidates."""
    if not sample_candidates:
        return 0
    avg_len = sum(len(c) + 1 for c in sample_candidates) / len(sample_candidates)
    return int(avg_len * total_count)


SortMode = Literal["length-asc", "length-desc", "alpha"]
VALID_SORT_MODES = ("length-asc", "length-desc", "alpha")


def sort_candidates(candidates: Iterator[str], sort_mode: SortMode) -> list[str]:
    """
    Materialize the candidate stream and sort it.

    Sorting requires the full set in memory (unlike the rest of the
    pipeline, which streams), so this is only used when the user
    explicitly asks for sorted output via --sort; the default streaming
    write path is untouched otherwise.
    """
    items = list(candidates)
    if sort_mode == "length-asc":
        items.sort(key=lambda s: (len(s), s))
    elif sort_mode == "length-desc":
        items.sort(key=lambda s: (-len(s), s))
    elif sort_mode == "alpha":
        items.sort()
    return items


def infer_output_format(output_path: str, explicit_format: str | None) -> OutputFormat:
    """
    Decide the output format: an explicit --format flag always wins;
    otherwise infer from the output file's extension (.csv / .jsonl /
    .json -> csv/jsonl); default to plain txt for anything else,
    including no extension or .txt.
    """
    if explicit_format:
        return explicit_format  # type: ignore[return-value]
    lower = output_path.lower()
    if lower.endswith(".csv"):
        return "csv"
    if lower.endswith(".jsonl") or lower.endswith(".json"):
        return "jsonl"
    return "txt"
