"""Transient user-facing status feedback through the selected desktop adapter."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

try:
    from .adapters import select_desktop_adapter
except ImportError:  # Installed module is also executable as a standalone script.
    from adapters import select_desktop_adapter


def emit_feedback(state: str, message: str, duration_ms: int, archi_bin_dir: Path) -> None:
    """Best-effort feedback must never block or alter command execution."""
    try:
        select_desktop_adapter(archi_bin_dir).feedback(state, message, duration_ms)
    except (AttributeError, ValueError):
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Display a transient ArCHi status overlay.")
    parser.add_argument("state")
    parser.add_argument("message")
    parser.add_argument("duration_ms", type=int, nargs="?", default=1200)
    args = parser.parse_args()
    if args.duration_ms < 100 or args.duration_ms > 10_000:
        parser.error("duration_ms must be between 100 and 10000")
    archi_bin_dir = Path(os.environ.get("ARCHI_BIN_DIR", Path.home() / ".local" / "bin"))
    emit_feedback(args.state, args.message, args.duration_ms, archi_bin_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
