"""Generation statistics: collection and JSON serialization."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict


@dataclass
class RunStats:
    mode: str = "generate"
    input_words: int = 0
    requested: int = 0
    generated: int = 0
    duplicates: int = 0
    possible: int = 0
    rules_enabled: int = 0
    output_file: str | None = None
    file_size_bytes: int = 0
    time_taken_seconds: float = 0.0
    generation_rate_per_sec: float = 0.0
    started_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))
    interrupted: bool = False
    per_word_counts: dict = field(default_factory=dict)

    def finalize_rate(self):
        if self.time_taken_seconds > 0:
            self.generation_rate_per_sec = self.generated / self.time_taken_seconds

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(asdict(self), indent=indent)

    def write_json_file(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
