"""Omarchy/Hyprland implementation of ArCHi action capabilities."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import time
from pathlib import Path

try:
    from ..text import normalize
except ImportError:  # Support the standalone installed router layout.
    from text import normalize

from .base import ActionResult


class OmarchyDesktopAdapter:
    provider_id = "omarchy.hyprland"
    _CAPABILITIES = frozenset({
        "app.close",
        "app.open",
        "audio.mute",
        "audio.volume.lower",
        "audio.volume.raise",
        "folder.close",
        "folder.open",
        "screenshot.capture",
        "session.lock",
        "window.close_active",
        "workspace.next",
        "workspace.previous",
        "visual.zoom.in",
        "visual.zoom.out",
        "visual.zoom.reset",
        "visual.zoom.restore",
    })
    _CLOSE_CONFIRM_ATTEMPTS = 4
    _CLOSE_CONFIRM_DELAY_SECONDS = 0.25
    _TERMINAL_CLASSES = frozenset({
        "foot", "footclient", "kitty", "alacritty", "ghostty",
        "commitchellhghostty", "orgwezfurlongwezterm", "wezterm",
        "orggnometerminal", "orggnomeconsole", "gnometerminal", "konsole",
        "xterm", "uxterm", "st256color",
    })

    def __init__(self, archi_bin_dir: Path):
        self.archi_bin_dir = archi_bin_dir

    def capabilities(self) -> frozenset[str]:
        return self._CAPABILITIES

    def context(self) -> dict:
        context = {
            "active_window_class": None,
            "active_window_title": None,
            "workspace_id": None,
            "workspace_name": None,
            "capture_status": "unavailable",
        }
        try:
            active_window = subprocess.run(
                ["hyprctl", "-j", "activewindow"],
                capture_output=True,
                text=True,
                timeout=1,
                check=False,
            )
            active_workspace = subprocess.run(
                ["hyprctl", "-j", "activeworkspace"],
                capture_output=True,
                text=True,
                timeout=1,
                check=False,
            )
            if active_window.returncode == 0:
                window = json.loads(active_window.stdout)
                context["active_window_class"] = window.get("class") or None
                context["active_window_title"] = window.get("title") or None
            if active_workspace.returncode == 0:
                workspace = json.loads(active_workspace.stdout)
                context["workspace_id"] = workspace.get("id")
                context["workspace_name"] = workspace.get("name") or None
            available = int(active_window.returncode == 0) + int(active_workspace.returncode == 0)
            context["capture_status"] = "available" if available == 2 else "partial" if available else "unavailable"
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
        return context

    def feedback(self, state: str, message: str, duration_ms: int) -> None:
        """Show a short, non-focus-stealing status overlay when enabled."""
        if os.environ.get("ARCHI_FEEDBACK", "minimal").casefold() == "off":
            return
        icons = {
            "listening": "microphone",
            "heard": "microphone",
            "success": "media-play",
            "unknown": "keyboard",
            "failed": "microphone-muted",
            "attention": "dialog-warning",
            "cancelled": "microphone-muted",
        }
        try:
            subprocess.Popen(
                [
                    "omarchy-osd",
                    "--icon", icons.get(state, "info"),
                    "--message", message,
                    "--duration", str(duration_ms),
                ],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass

    def execute(self, capability: str, payload: dict) -> ActionResult:
        if capability not in self._CAPABILITIES:
            return self._result("unsupported", capability, "capability is not provided")
        try:
            if capability == "app.open":
                return self._launch(capability, ["gtk-launch", payload["launcher_id"]])
            if capability == "app.close":
                return self._close_matching_window(capability, payload)
            if capability == "folder.open":
                return self._launch(capability, ["xdg-open", payload["path"]])
            if capability == "folder.close":
                return self._close_matching_window(capability, payload)
            if capability == "audio.volume.raise":
                return self._run(capability, ["omarchy-audio-output-volume", "raise"])
            if capability == "audio.volume.lower":
                return self._run(capability, ["omarchy-audio-output-volume", "lower"])
            if capability == "audio.mute":
                return self._run(
                    capability,
                    [str(self.archi_bin_dir / "archi-audio-output-mute"), payload["state"]],
                )
            if capability == "session.lock":
                return self._run(capability, ["loginctl", "lock-session"])
            if capability == "screenshot.capture":
                return self._launch(capability, ["omarchy-capture-screenshot"])
            if capability == "window.close_active":
                return self._run(capability, ["hyprctl", "dispatch", "hl.dsp.window.close()"])
            if capability.startswith("visual.zoom."):
                return self._zoom(capability, payload)
            workspace = "e+1" if capability == "workspace.next" else "e-1"
            return self._run(
                capability,
                ["hyprctl", "dispatch", f'hl.dsp.focus({{ workspace = "{workspace}" }})'],
            )
        except (KeyError, TypeError, ValueError) as error:
            return self._result("failed", capability, f"invalid payload: {error}")

    def zoom_factor(self) -> float | None:
        """Read the same Hyprland cursor zoom setting used by Omarchy's bindings."""
        try:
            result = subprocess.run(
                ["hyprctl", "-j", "getoption", "cursor.zoom_factor"],
                capture_output=True, text=True, timeout=2, check=False,
            )
            if result.returncode != 0:
                return None
            factor = float(json.loads(result.stdout)["float"])
            return factor if math.isfinite(factor) and 1 <= factor <= 10 else None
        except (OSError, subprocess.TimeoutExpired, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def _zoom(self, capability: str, payload: dict) -> ActionResult:
        current = self.zoom_factor()
        if current is None:
            return self._result("unavailable", capability, "Hyprland zoom state is unavailable")
        if capability == "visual.zoom.in":
            factor = min(10.0, current + 1.0)
        elif capability == "visual.zoom.out":
            factor = max(1.0, current - 1.0)
        elif capability == "visual.zoom.reset":
            factor = 1.0
        else:
            factor = payload.get("factor")
            if isinstance(factor, bool) or not isinstance(factor, (int, float)) or not math.isfinite(factor) or not 1 <= factor <= 10:
                return self._result("failed", capability, "invalid saved zoom factor")
        if abs(factor - current) < 0.001:
            return self._result("success", capability, "zoom already at requested level")
        # Use the same Lua config call as Omarchy's zoom bindings.
        return self._run(capability, ["hyprctl", "eval", f"hl.config({{ cursor = {{ zoom_factor = {factor:g} }} }})"])

    def _launch(self, capability: str, argv: list[str]) -> ActionResult:
        try:
            subprocess.Popen(argv, start_new_session=True)
        except OSError as error:
            return self._result("unavailable", capability, str(error))
        return self._result("success", capability)

    def _run(self, capability: str, argv: list[str]) -> ActionResult:
        try:
            result = subprocess.run(argv, capture_output=True, text=True, timeout=20, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            return self._result("unavailable", capability, str(error))
        detail = (getattr(result, "stderr", "") or getattr(result, "stdout", "")).strip() or None
        return self._result("success" if result.returncode == 0 else "failed", capability, detail)

    def _close_matching_window(self, capability: str, payload: dict) -> ActionResult:
        clients_result = self._clients(capability)
        if isinstance(clients_result, ActionResult):
            return clients_result
        clients = clients_result

        client = self._best_window_match(clients, payload)
        if client is None:
            return self._result("failed", capability, "no matching window")
        address = client.get("address")
        if not isinstance(address, str) or not re.fullmatch(r"0x[0-9a-fA-F]+", address):
            return self._result("failed", capability, "matching window has no valid address")

        dispatcher = f'hl.dsp.window.close({{ window = "address:{address}" }})'
        close_result = self._run(capability, ["hyprctl", "dispatch", dispatcher])
        if not close_result.succeeded:
            return close_result

        # The close request targets the window address directly, so neither the
        # active workspace nor its focus needs to change.  Only report success
        # after Hyprland no longer lists that exact target.  A window that stays
        # alive may be presenting its own save/discard/cancel dialog; this beta
        # deliberately flags attention instead of trying to operate that dialog.
        for attempt in range(self._CLOSE_CONFIRM_ATTEMPTS):
            remaining_result = self._clients(capability)
            if isinstance(remaining_result, ActionResult):
                return self._result("attention", capability, "close requested; unable to confirm window state")
            if not any(item.get("address") == address for item in remaining_result if isinstance(item, dict)):
                return self._result("success", capability, "window closed")
            if attempt + 1 < self._CLOSE_CONFIRM_ATTEMPTS:
                time.sleep(self._CLOSE_CONFIRM_DELAY_SECONDS)
        return self._result("attention", capability, "close requested; matching window still needs attention")

    def _clients(self, capability: str) -> list[dict] | ActionResult:
        try:
            result = subprocess.run(
                ["hyprctl", "-j", "clients"], capture_output=True, text=True, timeout=2, check=False
            )
            if result.returncode != 0:
                return self._result("unavailable", capability, (result.stderr or result.stdout).strip())
            clients = json.loads(result.stdout)
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
            return self._result("unavailable", capability, str(error))
        if not isinstance(clients, list):
            return self._result("unavailable", capability, "invalid client list")
        return clients

    @staticmethod
    def _best_window_match(clients: object, payload: dict) -> dict | None:
        desktop_stem = payload.get("desktop_id", "").removesuffix(".desktop")
        class_candidates = {
            window_key(value)
            for value in (
                payload.get("startup_wm_class", ""),
                payload.get("executable", ""),
                desktop_stem,
                desktop_stem.rsplit(".", 1)[-1],
                *payload.get("window_classes", []),
            )
            if value
        }
        title_candidates = {
            normalize(value)
            for value in [
                payload.get("app_name", ""),
                *payload.get("app_aliases", []),
                *payload.get("window_titles", []),
            ]
            if value
        }

        matches = []
        for client in clients if isinstance(clients, list) else []:
            if not isinstance(client, dict):
                continue
            classes = {
                window_key(value)
                for value in (client.get("class", ""), client.get("initialClass", ""))
                if value
            }
            title = normalize(client.get("title", ""))
            exact_title = title in title_candidates
            contained_title = any(
                len(candidate) >= 3 and f" {candidate} " in f" {title} " for candidate in title_candidates
            )
            class_match = bool(class_candidates & classes)
            title_match = exact_title or contained_title
            # GUI app titles can contain arbitrary document names. Only terminal
            # apps need a title fallback because they share their terminal's class.
            terminal_title_match = (
                payload.get("terminal", False)
                and bool(classes & OmarchyDesktopAdapter._TERMINAL_CLASSES)
                and title_match
            )
            matched = class_match and title_match if payload.get("require_title") else class_match or terminal_title_match
            if matched:
                focus = client.get("focusHistoryID")
                rank = focus if isinstance(focus, int) and focus >= 0 else 1_000_000
                matches.append((not class_match, rank, client))
        return min(matches, key=lambda item: item[:2])[2] if matches else None

    def _result(self, status: str, capability: str, detail: str | None = None) -> ActionResult:
        return ActionResult(status, self.provider_id, capability, detail)


def window_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())
