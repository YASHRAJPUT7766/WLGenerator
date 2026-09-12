"""
Smooth, throttled progress bar for streaming generation.

Designed to avoid flooding the terminal: renders are throttled to a
minimum interval regardless of how often update() is called.
"""
from __future__ import annotations

import sys
import time

from ui.theme import C, PRIMARY, SUCCESS, MUTED, style, clear_line
from utils.formatting import human_count, human_size, human_duration


class ProgressBar:
    def __init__(self, total: int, label: str = "Generating", width: int = 32,
                 min_interval: float = 0.08, stream=sys.stdout):
        self.total = max(total, 1)
        self.label = label
        self.width = width
        self.min_interval = min_interval
        self.stream = stream
        self.start_time = time.monotonic()
        self._last_render = 0.0
        self._current = 0
        self._bytes_written = 0
        self._interrupted = False
        self._enabled = stream.isatty()

    def update(self, current: int, bytes_written: int = 0, force: bool = False):
        self._current = current
        self._bytes_written = bytes_written
        now = time.monotonic()
        if not force and (now - self._last_render) < self.min_interval:
            return
        self._last_render = now
        self._render()

    def _render(self):
        if not self._enabled:
            return
        elapsed = max(time.monotonic() - self.start_time, 1e-9)
        frac = min(self._current / self.total, 1.0)
        filled = int(self.width * frac)
        bar = style("█" * filled, PRIMARY) + style("░" * (self.width - filled), MUTED)
        pct = f"{frac * 100:5.1f}%"
        rate = self._current / elapsed
        remaining = (self.total - self._current) / rate if rate > 0 else 0

        line = (
            f"  {style(self.label, C.BOLD)} [{bar}] {style(pct, C.BOLD)}  "
            f"{human_count(self._current)}/{human_count(self.total)}  "
            f"{style(f'{human_count(int(rate))}/s', MUTED)}  "
            f"{style('elapsed', MUTED)} {human_duration(elapsed)}  "
            f"{style('eta', MUTED)} {human_duration(remaining)}  "
            f"{style(human_size(self._bytes_written), MUTED)}"
        )
        clear_line()
        self.stream.write(line)
        self.stream.flush()

    def finish(self, interrupted: bool = False):
        self._interrupted = interrupted
        self._render_final()

    def _render_final(self):
        if not self._enabled:
            return
        from ui.theme import WARNING
        elapsed = max(time.monotonic() - self.start_time, 1e-9)
        clear_line()
        bar_color = WARNING if self._interrupted else SUCCESS
        bar = style("█" * self.width, bar_color)
        pct_val = min(self._current / self.total, 1.0) * 100
        suffix = style(" ⚠ interrupted", WARNING) if self._interrupted else ""
        line = (
            f"  {style(self.label, C.BOLD)} [{bar}] {style(f'{pct_val:5.1f}%', C.BOLD)}  "
            f"{human_count(self._current)}/{human_count(self.total)}  "
            f"{style(human_duration(elapsed), MUTED)}{suffix}"
        )
        self.stream.write(line + "\n")
        self.stream.flush()
