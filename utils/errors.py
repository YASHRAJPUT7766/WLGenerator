"""
Custom exception hierarchy.

All user-facing failures should raise a WLGenError subclass so the CLI
layer can catch them centrally and print a clean message instead of a
raw traceback (unless --debug is passed).
"""
from __future__ import annotations


class WLGenError(Exception):
    """Base class for all expected, user-facing WL Gen errors."""
    exit_code = 1


class ArgumentError(WLGenError):
    """Invalid or conflicting command-line arguments."""
    exit_code = 2


class InputFileError(WLGenError):
    """Problem reading an input wordlist file."""
    exit_code = 3


class ConfigError(WLGenError):
    """Problem loading or validating a configuration file."""
    exit_code = 4


class OutputError(WLGenError):
    """Problem writing the output file (permissions, disk space, encoding)."""
    exit_code = 5


class GenerationError(WLGenError):
    """Problem during the generation/rule-application phase."""
    exit_code = 6


class InterruptedGeneration(WLGenError):
    """Raised internally when the user cancels a long-running operation."""
    exit_code = 130
