"""Human-readable formatting helpers used throughout the UI."""
from __future__ import annotations


def human_count(n: int) -> str:
    """Format an integer with thousands separators, e.g. 1000000 -> '1,000,000'."""
    return f"{n:,}"


def human_size(num_bytes: float) -> str:
    """Format a byte count as a human-readable size."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def human_duration(seconds: float) -> str:
    """Format a duration in seconds as Hh Mm Ss / Ms / s form."""
    seconds = max(seconds, 0)
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, sec = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {sec}s"


def truncate(text: str, max_len: int = 60) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"
