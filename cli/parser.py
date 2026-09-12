"""
Custom argument parser for WL Gen.

A hand-rolled parser is used instead of argparse/click's default
model because WL Gen's spec requires:
  - short flags as the primary interface (-g, -wd, -w, -o, -n, ...)
  - a repeatable flag (-wd/--word) that can appear multiple times
  - flags that combine freely in any order
  - some short flags that are two characters (-wd, -wc) alongside
    single-character short flags (-g, -w, -n) with no ambiguity,
    which argparse's single-dash clustering does not support cleanly

The parser is intentionally simple and explicit: every flag is
registered with its arity (0 args / 1 arg / repeatable 1-arg) and the
parser raises ArgumentError with a clear message on anything invalid.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from utils.errors import ArgumentError

# Flag arity kinds
FLAG = "flag"          # boolean, takes no value
VALUE = "value"        # takes exactly one value, last occurrence wins
REPEATED = "repeated"  # takes one value, may appear multiple times (list)


@dataclass
class FlagSpec:
    dest: str
    short: list[str]
    long: list[str]
    kind: str
    help: str = ""
    metavar: str = ""
    category: str = "GENERAL"


@dataclass
class ParsedArgs:
    values: dict = field(default_factory=dict)

    def __getattr__(self, name):
        if name in self.values:
            return self.values[name]
        raise AttributeError(name)

    def get(self, name, default=None):
        return self.values.get(name, default)


class ArgParser:
    def __init__(self, specs: list[FlagSpec]):
        self.specs = specs
        self._lookup: dict[str, FlagSpec] = {}
        for spec in specs:
            for token in spec.short + spec.long:
                if token in self._lookup:
                    raise ValueError(f"Duplicate flag token registered: {token}")
                self._lookup[token] = spec

    def parse(self, argv: list[str]) -> ParsedArgs:
        values: dict = {}
        # Initialize defaults
        for spec in self.specs:
            if spec.kind == FLAG:
                values[spec.dest] = False
            elif spec.kind == REPEATED:
                values[spec.dest] = []
            else:
                values[spec.dest] = None

        i = 0
        positional: list[str] = []
        while i < len(argv):
            token = argv[i]

            if token == "--":
                positional.extend(argv[i + 1:])
                break

            if token.startswith("-") and token != "-":
                # Support --flag=value and -f=value syntax
                if "=" in token:
                    token_key, _, inline_value = token.partition("=")
                else:
                    token_key, inline_value = token, None

                spec = self._lookup.get(token_key)
                if spec is None:
                    raise ArgumentError(
                        f"Unrecognized option: '{token}'. "
                        f"Run 'wlgen -h' to see all available options."
                    )

                if spec.kind == FLAG:
                    if inline_value is not None:
                        raise ArgumentError(
                            f"Option '{token_key}' does not take a value."
                        )
                    values[spec.dest] = True
                    i += 1
                    continue

                # VALUE or REPEATED: need exactly one argument
                if inline_value is not None:
                    val = inline_value
                    i += 1
                else:
                    if i + 1 >= len(argv):
                        display = "/".join(spec.short + spec.long)
                        raise ArgumentError(
                            f"Option '{token_key}' ({display}) requires a value."
                        )
                    val = argv[i + 1]
                    i += 2

                if spec.kind == REPEATED:
                    values[spec.dest].append(val)
                else:
                    values[spec.dest] = val
                continue

            # Bare positional (not currently used by any WL Gen command,
            # but captured rather than silently dropped)
            positional.append(token)
            i += 1

        values["_positional"] = positional
        return ParsedArgs(values=values)

    def spec_for(self, dest: str) -> FlagSpec | None:
        for spec in self.specs:
            if spec.dest == dest:
                return spec
        return None
