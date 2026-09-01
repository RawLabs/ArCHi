"""Portable discovery of applications registered with the Linux desktop."""

from __future__ import annotations

import configparser
import os
import shlex
from dataclasses import dataclass
from pathlib import Path

try:
    from .text import normalize
except ImportError:  # Installed router is also executable as a standalone script.
    from text import normalize


@dataclass(frozen=True)
class DesktopApplication:
    desktop_id: str
    launcher_id: str
    name: str
    aliases: tuple[str, ...]
    startup_wm_class: str = ""
    executable: str | None = None

    def action_payload(self) -> dict:
        return {
            "app_name": self.name,
            "desktop_id": self.desktop_id,
            "launcher_id": self.launcher_id,
            "startup_wm_class": self.startup_wm_class,
            "executable": self.executable,
            "app_aliases": list(self.aliases),
        }


def application_dirs() -> list[Path]:
    """Return desktop-entry directories in user-to-system precedence order."""
    override = os.environ.get("ARCHI_APPLICATION_DIRS")
    if override is not None:
        candidates = [Path(value) for value in override.split(os.pathsep) if value]
    else:
        data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
        candidates = [data_home / "applications"]
        candidates.extend(Path(value) / "applications" for value in data_dirs.split(os.pathsep) if value)
        candidates.extend([
            data_home / "flatpak" / "exports" / "share" / "applications",
            Path("/var/lib/flatpak/exports/share/applications"),
            Path("/var/lib/snapd/desktop/applications"),
        ])

    result = []
    seen = set()
    for path in candidates:
        key = str(path)
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def desktop_bool(section: configparser.SectionProxy, key: str) -> bool:
    return section.get(key, "").casefold() in {"1", "true", "yes"}


def executable_name(exec_line: str) -> str | None:
    """Extract the executable basename for window-class matching only."""
    try:
        tokens = shlex.split(exec_line)
    except ValueError:
        return None
    if not tokens:
        return None
    index = 0
    if Path(tokens[0]).name == "env":
        index = 1
        while index < len(tokens) and "=" in tokens[index] and not tokens[index].startswith("/"):
            index += 1
    return Path(tokens[index]).name if index < len(tokens) else None


def scan_desktop_apps() -> list[DesktopApplication]:
    """Read launchable apps from the current XDG desktop-entry registry."""
    apps = []
    seen_ids = set()
    for directory in application_dirs():
        try:
            entries = sorted(directory.rglob("*.desktop"))
        except OSError:
            continue
        for path in entries:
            try:
                desktop_id = str(path.relative_to(directory)).replace(os.sep, "-")
            except ValueError:
                continue
            if desktop_id in seen_ids:
                continue
            seen_ids.add(desktop_id)

            parser = configparser.ConfigParser(interpolation=None, strict=False)
            parser.optionxform = str
            try:
                with path.open(encoding="utf-8") as stream:
                    parser.read_file(stream)
                section = parser["Desktop Entry"]
            except (OSError, UnicodeError, configparser.Error, KeyError):
                continue
            if desktop_bool(section, "Hidden"):
                continue
            if section.get("Type") != "Application" or desktop_bool(section, "NoDisplay"):
                continue
            name = section.get("Name", "").strip()
            exec_line = section.get("Exec", "").strip()
            if not name or (not exec_line and not desktop_bool(section, "DBusActivatable")):
                continue

            stem = desktop_id.removesuffix(".desktop")
            alias_values = {name, section.get("GenericName", "").strip(), stem, stem.rsplit(".", 1)[-1]}
            aliases = sorted({alias for value in alias_values if (alias := normalize(value))})
            apps.append(DesktopApplication(
                desktop_id=desktop_id,
                launcher_id=stem,
                name=name,
                aliases=tuple(aliases),
                startup_wm_class=section.get("StartupWMClass", "").strip(),
                executable=executable_name(exec_line),
            ))
    return apps
