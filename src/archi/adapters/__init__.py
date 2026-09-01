"""Selection boundary for machine-specific ArCHi action adapters."""

from __future__ import annotations

import os
from pathlib import Path

from .base import ActionResult, DesktopAdapter
from .omarchy import OmarchyDesktopAdapter


def select_desktop_adapter(archi_bin_dir: Path) -> DesktopAdapter:
    adapter_id = os.environ.get("ARCHI_DESKTOP_ADAPTER", "omarchy").casefold()
    if adapter_id in {"omarchy", "omarchy.hyprland"}:
        return OmarchyDesktopAdapter(archi_bin_dir)
    raise ValueError(f"unknown ArCHi desktop adapter: {adapter_id}")


__all__ = ["ActionResult", "DesktopAdapter", "select_desktop_adapter"]
