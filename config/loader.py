"""
Configuration file support (TOML).

Allows advanced users to define reusable rule sets (prefixes, suffixes,
numbers, symbols, separators, case rules, ordering, dedup, output
preferences) in a config file instead of passing everything via flags.
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field

from rules.definitions import RuleSet
from utils.errors import ConfigError

VALID_CASE_MODES = {"lower", "upper", "capitalize", "title"}


@dataclass
class AppConfig:
    raw: dict = field(default_factory=dict)

    def to_ruleset(self, overrides: RuleSet | None = None) -> RuleSet:
        """
        Build a RuleSet from config values. If `overrides` is given,
        CLI-supplied values in it take precedence over config values
        (overrides is assumed pre-populated only where the user passed
        explicit flags).
        """
        gen = self.raw.get("generation", {})
        out = self.raw.get("output", {})

        rs = RuleSet(
            case_modes=gen.get("case", ["lower"]),
            prefixes=gen.get("prefixes", []),
            suffixes=gen.get("suffixes", []),
            numbers=[str(n) for n in gen.get("numbers", [])],
            symbols=gen.get("symbols", []),
            separators=gen.get("separators", [""]),
            use_substitutions=gen.get("substitutions", False),
            combine_words=gen.get("combine_words", False),
            min_length=gen.get("min_length"),
            max_length=gen.get("max_length"),
            deduplicate=out.get("deduplicate", True),
        )
        return rs


def load_config(path: str) -> AppConfig:
    if not os.path.exists(path):
        raise ConfigError(f"Configuration file not found: '{path}'")
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML syntax in '{path}': {exc}")
    except OSError as exc:
        raise ConfigError(f"Could not read configuration file '{path}': {exc}")

    validate_config(data, path)
    return AppConfig(raw=data)


def validate_config(data: dict, path: str):
    gen = data.get("generation", {})
    if not isinstance(gen, dict):
        raise ConfigError(f"'[generation]' section in '{path}' must be a table.")

    case_modes = gen.get("case", ["lower"])
    if not isinstance(case_modes, list) or not all(isinstance(c, str) for c in case_modes):
        raise ConfigError(f"'generation.case' in '{path}' must be a list of strings.")
    for mode in case_modes:
        if mode not in VALID_CASE_MODES:
            raise ConfigError(
                f"Invalid case mode '{mode}' in '{path}'. "
                f"Valid options: {', '.join(sorted(VALID_CASE_MODES))}."
            )

    for key in ("prefixes", "suffixes", "symbols", "separators"):
        if key in gen and not isinstance(gen[key], list):
            raise ConfigError(f"'generation.{key}' in '{path}' must be a list.")

    if "numbers" in gen and not isinstance(gen["numbers"], list):
        raise ConfigError(f"'generation.numbers' in '{path}' must be a list.")

    min_len = gen.get("min_length")
    max_len = gen.get("max_length")
    if min_len is not None and not isinstance(min_len, int):
        raise ConfigError(f"'generation.min_length' in '{path}' must be an integer.")
    if max_len is not None and not isinstance(max_len, int):
        raise ConfigError(f"'generation.max_length' in '{path}' must be an integer.")
    if min_len is not None and max_len is not None and min_len > max_len:
        raise ConfigError(f"'generation.min_length' cannot exceed 'max_length' in '{path}'.")

    output = data.get("output", {})
    if output and not isinstance(output, dict):
        raise ConfigError(f"'[output]' section in '{path}' must be a table.")
    if "deduplicate" in output and not isinstance(output["deduplicate"], bool):
        raise ConfigError(f"'output.deduplicate' in '{path}' must be true or false.")
