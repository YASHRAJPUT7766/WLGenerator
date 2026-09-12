"""
Resume support for interrupted generation runs.

WL Gen's generation is deterministic for a given (seed words, ruleset,
requested count) combination -- the same inputs always produce candidates
in the same order. That determinism is what makes resume possible without
storing any of the generated data itself: a small sidecar JSON file next
to the output records how many unique candidates had already been written
when the run stopped, plus enough of the run's parameters to confirm a
`--resume` invocation is picking the *same* run back up rather than a
different one.

On `--resume`, WL Gen re-derives the candidate stream from scratch,
silently skips the first N (already-written) unique candidates, and
appends the rest to the existing output file -- so nothing already on
disk is duplicated or overwritten.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass

from utils.errors import OutputError

RESUME_SUFFIX = ".wlgen-resume.json"


def resume_path_for(output_path: str) -> str:
    return output_path + RESUME_SUFFIX


def _fingerprint(words: list[str], ruleset_repr: str, requested: int) -> str:
    """
    A short hash of the run's defining parameters (seed words, resolved
    rule set, requested count). Used only to sanity-check that --resume
    is being applied to the same run that was interrupted, not to a
    differently-configured one pointed at the same output file.
    """
    payload = json.dumps(
        {"words": words, "ruleset": ruleset_repr, "requested": requested},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass
class ResumeState:
    written: int
    fingerprint: str


def save_resume_state(output_path: str, words: list[str], ruleset_repr: str,
                       requested: int, written: int) -> None:
    """Write (or overwrite) the sidecar resume file after a run stops."""
    state = {
        "fingerprint": _fingerprint(words, ruleset_repr, requested),
        "written": written,
    }
    try:
        with open(resume_path_for(output_path), "w", encoding="utf-8") as f:
            json.dump(state, f)
    except OSError:
        # Resume support is a convenience, not a correctness requirement --
        # if we can't write the sidecar file, the run itself still succeeded.
        pass


def clear_resume_state(output_path: str) -> None:
    """Remove the sidecar file once a run completes fully (nothing to resume)."""
    path = resume_path_for(output_path)
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def load_resume_state(output_path: str, words: list[str], ruleset_repr: str,
                       requested: int) -> ResumeState | None:
    """
    Load and validate the sidecar resume file for `output_path`, if any.
    Returns None if there's nothing to resume. Raises OutputError if a
    resume file exists but doesn't match the current run's parameters
    (seed words, rules, or requested count changed) or the output file
    it refers to is missing -- resuming from a mismatched or missing
    base would silently produce a wrong or corrupt wordlist.
    """
    path = resume_path_for(output_path)
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise OutputError(f"Could not read resume state '{path}': {exc}")

    if not os.path.exists(output_path):
        raise OutputError(
            f"Resume file '{path}' exists but output file '{output_path}' "
            f"is missing. Remove the resume file to start a fresh run, or "
            f"restore the original output file."
        )

    expected_fp = _fingerprint(words, ruleset_repr, requested)
    if state.get("fingerprint") != expected_fp:
        raise OutputError(
            f"Resume file '{path}' does not match the current command's "
            f"words/rules/count -- it looks like it belongs to a different "
            f"run. Remove '{path}' to start fresh, or re-run with the exact "
            f"same flags as the interrupted run."
        )

    return ResumeState(written=state.get("written", 0), fingerprint=expected_fp)
