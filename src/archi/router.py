#!/usr/bin/env python3
"""Deterministic ArCHi command router with local comparison instrumentation."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
import tomllib
import uuid
from pathlib import Path

try:
    from .adapters import ActionResult, select_desktop_adapter
    from .applications import load_app_aliases, scan_desktop_apps
    from .feedback import emit_feedback
    from .text import normalize
except ImportError:  # Installed router is also executable as a standalone script.
    from adapters import ActionResult, select_desktop_adapter
    from applications import load_app_aliases, scan_desktop_apps
    from feedback import emit_feedback
    from text import normalize


BASE = Path(__file__).resolve().parent
SOURCE_REGISTRY_PATH = BASE.parents[1] / "config" / "commands.toml"
DEPLOYED_REGISTRY_PATH = BASE / "commands.toml"
REGISTRY_PATH = Path(os.environ.get(
    "ARCHI_COMMANDS_PATH",
    SOURCE_REGISTRY_PATH if SOURCE_REGISTRY_PATH.is_file() else DEPLOYED_REGISTRY_PATH,
))
SOURCE_INTENTS_PATH = BASE.parents[1] / "config" / "intents.yaml"
DEPLOYED_INTENTS_PATH = BASE / "intents.yaml"
INTENTS_PATH = Path(os.environ.get(
    "ARCHI_INTENTS_PATH",
    SOURCE_INTENTS_PATH if SOURCE_INTENTS_PATH.is_file() else DEPLOYED_INTENTS_PATH,
))
VENDOR_DIR = BASE / "vendor"
if VENDOR_DIR.is_dir():
    sys.path.insert(0, str(VENDOR_DIR))
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "archi"
LOG_PATH = Path(os.environ.get("ARCHI_LOG_PATH", Path.home() / ".local" / "state" / "archi" / "commands.jsonl"))
OFF_RECORD_PATH = RUNTIME_DIR / "off-record"
PENDING_PATH = RUNTIME_DIR / "pending.json"
ADJUSTMENT_PATH = RUNTIME_DIR / "adjustment.json"
ARCHI_BIN_DIR = Path(os.environ.get("ARCHI_BIN_DIR", Path.home() / ".local" / "bin"))
SPEAK = os.environ.get("ARCHI_TTS_SAY", str(ARCHI_BIN_DIR / "pocket-tts-say"))
SCHEMA_VERSION = 4
INPUT_SOURCE = "voxtype-control"
APP_ACTION_VERBS = {
    "open": "app.open",
    "launch": "app.open",
    "start": "app.open",
    "close": "app.close",
    "quit": "app.close",
    "exit": "app.close",
}


def dynamic_app_commands() -> list[dict]:
    """Build open/close commands, omitting aliases shared by multiple apps."""
    apps = scan_desktop_apps()
    custom_aliases = load_app_aliases()
    aliases_by_desktop_id = {
        app.desktop_id: set(app.aliases) | custom_aliases.get(app.desktop_id, set())
        for app in apps
    }
    owners: dict[str, set[str]] = {}
    for app in apps:
        for alias in aliases_by_desktop_id[app.desktop_id]:
            owners.setdefault(alias, set()).add(app.desktop_id)

    commands = []
    for app in apps:
        aliases = sorted(alias for alias in aliases_by_desktop_id[app.desktop_id] if len(owners[alias]) == 1)
        if not aliases:
            continue
        payload = {**app.action_payload(), "app_aliases": aliases}
        commands.extend([
            {
                "id": f"open_app:{app.desktop_id}",
                "phrases": [f"{verb} {alias}" for alias in aliases for verb in ("open", "launch", "start")],
                "action": "capability",
                "capability": "app.open",
                "payload": payload,
                "desktop_id": app.desktop_id,
                "reply": f"Opening {app.name}.",
            },
            {
                "id": f"close_app:{app.desktop_id}",
                "phrases": [f"{verb} {alias}" for alias in aliases for verb in ("close", "quit", "exit")],
                "action": "capability",
                "capability": "app.close",
                "payload": payload,
                "desktop_id": app.desktop_id,
                "reply": f"Closed {app.name}.",
            },
        ])
    return commands


def load_commands() -> tuple[dict[str, dict], dict[str, dict]]:
    with REGISTRY_PATH.open("rb") as stream:
        entries = tomllib.load(stream).get("commands", [])
    by_phrase: dict[str, dict] = {}
    by_id: dict[str, dict] = {}
    for entry in [*entries, *dynamic_app_commands()]:
        command_id = entry["id"]
        if command_id in by_id:
            raise ValueError(f"duplicate command id: {command_id}")
        by_id[command_id] = entry
        for phrase in entry.get("phrases", []):
            key = normalize(phrase)
            if key in by_phrase:
                if entry.get("desktop_id"):
                    continue
                raise ValueError(f"duplicate command phrase: {phrase}")
            by_phrase[key] = entry
    return by_phrase, by_id


def compact_app_alias(value: str) -> str:
    """Remove spaces so separately spoken letters can match an app name."""
    return "".join(normalize(value).split())


def phonetic_app_alias(value: str) -> str:
    """Treat q, c, and k as equivalent in an app name spoken aloud."""
    return compact_app_alias(value).translate(str.maketrans({"q": "k", "c": "k"}))


def one_edit_apart(left: str, right: str) -> bool:
    """Return whether two strings differ by at most one insertion, deletion, or change."""
    if left == right:
        return True
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) > len(right):
        left, right = right, left
    index = other_index = edits = 0
    while index < len(left) and other_index < len(right):
        if left[index] == right[other_index]:
            index += 1
            other_index += 1
            continue
        edits += 1
        if edits > 1:
            return False
        if len(left) == len(right):
            index += 1
        other_index += 1
    return True


def split_app_command(phrase: str) -> tuple[str, str] | None:
    """Extract an open/close verb and app target, accepting a missing separator."""
    for verb, capability in APP_ACTION_VERBS.items():
        if phrase.startswith(f"{verb} "):
            return capability, phrase[len(verb):].strip()
        if phrase.startswith(verb) and len(phrase) > len(verb):
            return capability, phrase[len(verb):].strip()
    return None


def resolve_dynamic_app(phrase: str, commands_by_id: dict[str, dict]) -> tuple[dict, str] | None:
    """Resolve a unique installed app after exact command matching has failed.

    This intentionally applies only to application commands. Operational commands
    remain exact registry phrases, while desktop-entry aliases accept natural
    spaces, separately spoken letters, and the common q/c/k transcription swap.
    A one-character correction is permitted only for names of five or more
    characters and only where it identifies one installed application.
    """
    parsed = split_app_command(phrase)
    if parsed is None:
        return None
    capability, target = parsed
    if not target:
        return None

    target_compact = compact_app_alias(target)
    target_phonetic = phonetic_app_alias(target)
    matches: dict[str, tuple[dict, str]] = {}
    fuzzy_matches: dict[str, tuple[dict, str]] = {}
    for command in commands_by_id.values():
        if command.get("capability") != capability or not command.get("desktop_id"):
            continue
        for alias in command.get("payload", {}).get("app_aliases", []):
            compact_alias = compact_app_alias(alias)
            if target_compact == compact_alias or target_phonetic == phonetic_app_alias(alias):
                matches[command["id"]] = (command, alias)
            elif (
                len(target_phonetic) >= 5
                and len(compact_alias) >= 5
                and one_edit_apart(target_phonetic, phonetic_app_alias(alias))
            ):
                fuzzy_matches[command["id"]] = (command, alias)

    if len(matches) == 1:
        return next(iter(matches.values()))
    if not matches and len(fuzzy_matches) == 1:
        return next(iter(fuzzy_matches.values()))
    return None


def off_record() -> bool:
    return OFF_RECORD_PATH.exists()


def set_off_record(enabled: bool) -> None:
    RUNTIME_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    if enabled:
        OFF_RECORD_PATH.touch(mode=0o600, exist_ok=True)
    else:
        OFF_RECORD_PATH.unlink(missing_ok=True)


def load_pending() -> dict | None:
    try:
        pending = json.loads(PENDING_PATH.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(pending, dict):
        return None
    expires = pending.get("expires")
    targets = pending.get("targets")
    if (
        isinstance(expires, bool)
        or not isinstance(expires, (int, float))
        or not math.isfinite(expires)
        or expires <= time.time()
        or not isinstance(pending.get("command_id"), str)
        or not isinstance(targets, dict)
        or any(not isinstance(key, str) or not isinstance(value, str) for key, value in targets.items())
    ):
        return None
    return pending


def save_pending(command: dict) -> None:
    RUNTIME_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    payload = {
        "command_id": command["id"],
        "targets": command.get("targets", {}),
        "expires": time.time() + 10,
    }
    PENDING_PATH.write_text(json.dumps(payload))
    os.chmod(PENDING_PATH, 0o600)


def clear_pending() -> None:
    PENDING_PATH.unlink(missing_ok=True)


def load_adjustment() -> dict | None:
    try:
        adjustment = json.loads(ADJUSTMENT_PATH.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(adjustment, dict) or adjustment.get("family") not in ("zoom", "volume"):
        return None
    expires = adjustment.get("expires")
    if isinstance(expires, bool) or not isinstance(expires, (int, float)) or not math.isfinite(expires):
        return None
    if adjustment["family"] == "zoom" and any(
        isinstance(adjustment.get(key), bool)
        or not isinstance(adjustment.get(key), (int, float))
        or not math.isfinite(adjustment[key])
        or not 1 <= adjustment[key] <= 10
        for key in ("origin", "last_factor")
    ):
        return None
    if adjustment.get("expires", 0) <= time.time():
        return None
    return adjustment


def save_adjustment(family: str, origin: float | None = None, last_factor: float | None = None) -> None:
    RUNTIME_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    payload = {"family": family, "origin": origin, "last_factor": last_factor, "expires": time.time() + 120}
    temporary = ADJUSTMENT_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload))
    os.chmod(temporary, 0o600)
    temporary.replace(ADJUSTMENT_PATH)


def clear_adjustment() -> None:
    ADJUSTMENT_PATH.unlink(missing_ok=True)


def current_zoom_factor() -> float | None:
    try:
        adapter = select_desktop_adapter(ARCHI_BIN_DIR)
        return adapter.zoom_factor()
    except (ValueError, AttributeError):
        return None


def speak(text: str, dry_run: bool) -> None:
    if not text or dry_run:
        return
    try:
        subprocess.run([SPEAK, text], check=False, timeout=130)
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"ArCHi speech unavailable: {error}", file=sys.stderr)


def show_feedback(state: str, message: str, duration_ms: int, dry_run: bool) -> None:
    if not dry_run:
        emit_feedback(state, message, duration_ms, ARCHI_BIN_DIR)


def log_event(event: dict, suppressed: bool) -> None:
    if suppressed:
        return
    event["comparison"] = classify_shadow(event)
    try:
        LOG_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
        os.chmod(LOG_PATH, 0o600)
    except OSError as error:
        print(f"ArCHi diagnostic log unavailable: {error}", file=sys.stderr)


def desktop_context() -> dict:
    """Capture read-only context through the selected desktop adapter."""
    try:
        return select_desktop_adapter(ARCHI_BIN_DIR).context()
    except ValueError as error:
        return {"capture_status": "unavailable", "detail": str(error)}


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def performance_context() -> dict:
    """Capture lightweight local performance state for tuning analysis."""
    context = {
        "capture_status": "partial",
        "on_ac_power": None,
        "battery_percent": None,
        "battery_status": None,
        "power_profile": None,
        "cpu_governor": read_text(Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")),
        "load_average_1m": round(os.getloadavg()[0], 2),
        "memory_available_mib": None,
    }
    for line in (read_text(Path("/proc/meminfo")) or "").splitlines():
        if line.startswith("MemAvailable:"):
            try:
                context["memory_available_mib"] = round(int(line.split()[1]) / 1024)
            except (IndexError, ValueError):
                pass
            break

    battery_paths: list[Path] = []
    ac_states: list[bool] = []
    try:
        for supply in Path("/sys/class/power_supply").iterdir():
            supply_type = read_text(supply / "type")
            if supply_type == "Battery":
                battery_paths.append(supply)
            elif supply_type in {"Mains", "USB", "USB_C"}:
                online = read_text(supply / "online")
                if online in {"0", "1"}:
                    ac_states.append(online == "1")
    except OSError:
        pass
    if ac_states:
        context["on_ac_power"] = any(ac_states)
    if battery_paths:
        battery = battery_paths[0]
        capacity = read_text(battery / "capacity")
        try:
            context["battery_percent"] = int(capacity) if capacity is not None else None
        except ValueError:
            pass
        context["battery_status"] = read_text(battery / "status")

    try:
        profile = subprocess.run(
            ["powerprofilesctl", "get"], capture_output=True, text=True, timeout=0.25, check=False
        )
        if profile.returncode == 0:
            context["power_profile"] = profile.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        pass

    if any(value is not None for value in context.values() if value != "partial"):
        context["capture_status"] = "available"
    return context


def capture_context() -> dict:
    """Read timing exported by the push-to-talk wrapper, if available."""
    timings = {}
    for field, variable in (
        ("session_duration_ms", "ARCHI_CAPTURE_DURATION_MS"),
        ("transcript_wait_ms", "ARCHI_TRANSCRIPT_WAIT_MS"),
    ):
        try:
            value = int(os.environ.get(variable, ""))
            timings[field] = value if value >= 0 else None
        except ValueError:
            timings[field] = None
    return timings


def hassil_shadow(phrase: str, commands_by_id: dict[str, dict] | None) -> dict:
    """Compare an independent HassIL grammar without allowing it to execute."""
    if not phrase:
        return {"parser": "hassil", "status": "skipped", "reason": "empty_phrase", "duration_ms": 0}
    if commands_by_id is not None:
        for command in commands_by_id.values():
            if command.get("desktop_id") and phrase in map(normalize, command.get("phrases", [])):
                return {
                    "parser": "hassil",
                    "status": "skipped",
                    "reason": "dynamic_app_registry",
                    "duration_ms": 0,
                }
    started = time.monotonic()
    try:
        from hassil.intents import Intents
        from hassil.recognize import recognize
    except ImportError:
        return {"parser": "hassil", "status": "not_installed", "duration_ms": 0}

    try:
        if not INTENTS_PATH.is_file():
            return {
                "parser": "hassil",
                "status": "schema_missing",
                "duration_ms": round((time.monotonic() - started) * 1000),
            }
        if commands_by_id is None:
            _, commands_by_id = load_commands()
        intents = Intents.from_files([INTENTS_PATH])
        match = recognize(phrase, intents)
        duration_ms = round((time.monotonic() - started) * 1000)
        if match is None:
            return {"parser": "hassil", "status": "no_match", "duration_ms": duration_ms}
        command_id = match.entities.get("command_id")
        command_id_value = command_id.value if command_id else None
        if command_id_value not in commands_by_id:
            return {
                "parser": "hassil",
                "status": "invalid_command",
                "intent_id": match.intent.name,
                "command_id": command_id_value,
                "duration_ms": duration_ms,
            }
        return {
            "parser": "hassil",
            "status": "matched",
            "intent_id": match.intent.name,
            "command_id": command_id_value,
            "duration_ms": duration_ms,
        }
    except Exception as error:
        return {
            "parser": "hassil",
            "status": "error",
            "error_type": type(error).__name__,
            "duration_ms": round((time.monotonic() - started) * 1000),
        }


def classify_shadow(event: dict) -> str:
    """Label the production/shadow relationship for test reporting."""
    shadow = event.get("shadow") or {}
    shadow_status = shadow.get("status")
    production_id = event.get("matched_command_id")
    shadow_id = shadow.get("command_id") if shadow_status == "matched" else None

    if event.get("clarification_count", 0) > 0:
        return "not_comparable"
    if shadow_status in {"not_installed", "schema_missing", "error", "invalid_command", "test", None}:
        return "not_comparable"
    if event.get("event_type") == "silent_input" or shadow_status == "skipped":
        return "agree" if not production_id else "not_comparable"
    if production_id:
        if shadow_status == "no_match":
            return "shadow_regression"
        if shadow_status == "matched":
            return "agree" if shadow_id == production_id else "conflict"
        return "not_comparable"
    if shadow_status == "matched":
        return "shadow_extension"
    if shadow_status == "no_match":
        return "agree"
    return "not_comparable"


def event_base(
    raw_text: str, phrase: str, was_off_record: bool, commands_by_id: dict[str, dict] | None = None
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": uuid.uuid4().hex,
        "timestamp": time.time(),
        "session_id": os.environ.get("ARCHI_SESSION_ID"),
        "event_type": "command",
        "input_source": INPUT_SOURCE,
        "transcript": raw_text,
        "normalized_phrase": phrase,
        "matched_command_id": None,
        "matched_alias": phrase,
        "result": None,
        "clarification_count": 0,
        "execution_status": "not_run",
        "context": desktop_context(),
        "capture": capture_context(),
        "performance": performance_context(),
        "shadow": hassil_shadow(phrase, commands_by_id),
        "logging_outcome": "recorded",
        "off_record": was_off_record,
    }


def record_silent(reason: str = "no_transcript", dry_run: bool = False) -> dict:
    started = time.monotonic()
    was_off_record = off_record()
    event = event_base("", "", was_off_record)
    event.update({
        "event_type": "silent_input",
        "result": "silent",
        "silent_reason": reason,
        "duration_ms": round((time.monotonic() - started) * 1000),
    })
    show_feedback("unknown", "No command heard.", 1800, dry_run)
    log_event(event, was_off_record)
    return {"status": "silent", "reason": reason}


def feedback_phrase(phrase: str) -> str:
    """Keep a transcript cue compact enough for a transient overlay."""
    return phrase if len(phrase) <= 80 else f"{phrase[:77]}..."


def expand_argv(argv: list[str]) -> list[str]:
    substitutions = {
        "{home}": str(Path.home()),
        "{archi_bin}": str(ARCHI_BIN_DIR),
        "{archi_home}": str(DEPLOYED_REGISTRY_PATH.parent),
    }
    expanded = []
    for argument in argv:
        for token, value in substitutions.items():
            argument = argument.replace(token, value)
        expanded.append(argument)
    return expanded


def expand_payload(payload: dict) -> dict:
    substitutions = {
        "{home}": str(Path.home()),
        "{archi_bin}": str(ARCHI_BIN_DIR),
        "{archi_home}": str(DEPLOYED_REGISTRY_PATH.parent),
    }
    expanded = {}
    for key, value in payload.items():
        if isinstance(value, str):
            for token, replacement in substitutions.items():
                value = value.replace(token, replacement)
        expanded[key] = value
    return expanded


def execute(command: dict, dry_run: bool) -> ActionResult:
    action = command.get("action")
    if action in {"reply", "clarify", "mode_off_record", "mode_logging_on"}:
        return ActionResult("success", "archi.core", action, None)
    argv = expand_argv(command.get("argv", []))
    if action == "capability":
        capability = command.get("capability", "")
        try:
            adapter = select_desktop_adapter(ARCHI_BIN_DIR)
        except ValueError as error:
            return ActionResult("unavailable", "none", capability, str(error))
        if dry_run:
            status = "success" if capability in adapter.capabilities() else "unsupported"
            return ActionResult(status, adapter.provider_id, capability, None)
        return adapter.execute(capability, expand_payload(command.get("payload", {})))
    if dry_run:
        return ActionResult("success", "archi.argv", action or "unknown", None)
    try:
        if action == "launch":
            subprocess.Popen(argv, start_new_session=True)
            return ActionResult("success", "archi.argv", action, None)
        if action == "run":
            result = subprocess.run(argv, timeout=20, check=False)
            status = "success" if result.returncode == 0 else "failed"
            return ActionResult(status, "archi.argv", action, None)
    except (OSError, subprocess.TimeoutExpired) as error:
        return ActionResult("unavailable", "archi.argv", action or "unknown", str(error))
    return ActionResult("unsupported", "archi.argv", action or "unknown", None)


def route(text: str, dry_run: bool = False) -> dict:
    started = time.monotonic()
    raw_text = text.strip()
    phrase = normalize(text)
    if not phrase:
        return record_silent("empty_command", dry_run)
    display_phrase = feedback_phrase(phrase)
    show_feedback("heard", f"Heard: {display_phrase}", 1000, dry_run)
    was_off_record = off_record()
    by_phrase, by_id = load_commands()
    pending = load_pending()
    adjustment = load_adjustment()
    command = None
    alias = phrase
    clarification_count = 0

    cancellation = phrase in {"cancel", "cancel that", "never mind", "nevermind"}
    if pending and cancellation:
        if not dry_run:
            clear_pending()
        result = {"status": "cancelled", "reply": "Cancelled."}
        show_feedback("cancelled", "Cancelled.", 900, dry_run)
        speak(result["reply"], dry_run)
        event = event_base(raw_text, phrase, was_off_record, by_id)
        event.update({
            "matched_command_id": pending["command_id"], "matched_alias": alias,
            "result": result["status"], "clarification_count": 1,
            "execution_status": "not_run",
            "duration_ms": round((time.monotonic() - started) * 1000),
        })
        log_event(event, was_off_record)
        return result

    if cancellation and not adjustment:
        reply = "Nothing to cancel."
        show_feedback("cancelled", reply, 1200, dry_run)
        speak(reply, dry_run)
        return {"status": "cancelled", "reply": reply}

    if pending:
        target_id = pending.get("targets", {}).get(phrase)
        if target_id:
            command = by_id.get(target_id)
            clarification_count = 1
            if not dry_run:
                clear_pending()

    if command is None:
        command = by_phrase.get(phrase)

    if command is None and not pending and adjustment and phrase in {"more", "a little more", "increase it", "less", "a little less", "decrease it"}:
        family = adjustment.get("family")
        increase = phrase in {"more", "a little more", "increase it"}
        followups = {
            "zoom": ("zoom_in", "zoom_less"),
            "volume": ("volume_up", "volume_down"),
        }
        if family in followups:
            command = by_id.get(followups[family][0 if increase else 1])

    if command is None and cancellation and adjustment:
        if adjustment.get("family") == "zoom" and adjustment.get("origin") is not None:
            last_factor = adjustment.get("last_factor")
            actual_factor = current_zoom_factor() if not dry_run else last_factor
            if last_factor is not None and actual_factor is not None and abs(actual_factor - last_factor) > 0.01:
                if not dry_run:
                    clear_adjustment()
                reply = "Zoom changed elsewhere. I left it as it is."
                show_feedback("cancelled", reply, 2200, dry_run)
                speak(reply, dry_run)
                return {"status": "cancelled", "reply": reply}
            restore = by_id.get("zoom_restore")
            if restore:
                command = {**restore, "payload": {"factor": adjustment["origin"]}}
        else:
            if not dry_run:
                clear_adjustment()
            reply = "Cancelled."
            show_feedback("cancelled", reply, 900, dry_run)
            speak(reply, dry_run)
            return {"status": "cancelled", "reply": reply}

    if command is None:
        resolved_app = resolve_dynamic_app(phrase, by_id)
        if resolved_app is not None:
            command, alias = resolved_app

    if command is None:
        reply = "I don't know that command yet."
        show_feedback("unknown", f"Heard: {display_phrase}  No match.", 3000, dry_run)
        speak(reply, dry_run)
        result = {"status": "unknown", "reply": reply}
        event = event_base(raw_text, phrase, was_off_record, by_id)
        event.update({
            "matched_alias": alias, "result": result["status"],
            "clarification_count": clarification_count,
            "duration_ms": round((time.monotonic() - started) * 1000),
        })
        log_event(event, was_off_record)
        return result

    command_id = command["id"]
    action = command.get("action")
    if pending and not dry_run:
        clear_pending()

    if action == "clarify":
        if not dry_run:
            save_pending(command)
        reply = command["prompt"]
        show_feedback("unknown", "Which target should I use?", 2200, dry_run)
        speak(reply, dry_run)
        result = {"status": "clarifying", "command_id": command_id, "reply": reply}
        event = event_base(raw_text, phrase, was_off_record, by_id)
        event.update({
            "matched_command_id": command_id, "matched_alias": alias,
            "result": result["status"], "clarification_count": clarification_count,
            "execution_status": "not_run",
            "duration_ms": round((time.monotonic() - started) * 1000),
        })
        log_event(event, was_off_record)
        return result

    if action == "mode_off_record":
        if not dry_run:
            set_off_record(True)
        speak(command.get("reply", ""), dry_run)
        return {"status": "off_record", "command_id": command_id}

    if action == "mode_logging_on":
        if not dry_run:
            set_off_record(False)
        speak(command.get("reply", ""), dry_run)
        return {"status": "logging_on", "command_id": command_id}

    reply = command.get("reply", "")
    capability = command.get("capability", "")
    zoom_origin = None
    if capability in {"visual.zoom.in", "visual.zoom.out"} and (not adjustment or adjustment.get("family") != "zoom") and not dry_run:
        zoom_origin = current_zoom_factor()
    if command.get("reply_before"):
        speak(reply, dry_run)
    execution = execute(command, dry_run)
    success = execution.succeeded
    if success and execution.detail == "zoom already at requested level":
        reply = "Zoom is already at that level."
    if success and not dry_run:
        if capability in {"visual.zoom.in", "visual.zoom.out"}:
            origin = adjustment.get("origin") if adjustment and adjustment.get("family") == "zoom" else zoom_origin
            last_factor = current_zoom_factor()
            if origin is not None and last_factor is not None:
                save_adjustment("zoom", origin, last_factor)
            else:
                clear_adjustment()
        elif capability == "visual.zoom.reset" or capability == "visual.zoom.restore":
            clear_adjustment()
        elif capability in {"audio.volume.raise", "audio.volume.lower"}:
            save_adjustment("volume")
        else:
            clear_adjustment()
    needs_attention = execution.status == "attention"
    if needs_attention:
        app_name = command.get("payload", {}).get("app_name")
        reply = f"{app_name} needs attention." if app_name else "That application needs attention."
        speak(reply, dry_run)
        show_feedback("attention", reply, 3500, dry_run)
    elif success and not command.get("reply_before"):
        speak(reply, dry_run)
    if not success and not needs_attention:
        reply = "Omarchy zoom is unavailable." if capability.startswith("visual.zoom.") and execution.status == "unavailable" else "That command failed."
        speak(reply, dry_run)
        show_feedback("failed", reply, 3000, dry_run)
    elif success:
        show_feedback("cancelled" if command_id == "zoom_restore" else "success", reply or "Command complete.", 1300, dry_run)

    result = {
        "status": "cancelled" if success and command_id == "zoom_restore" else "success" if success else "attention" if needs_attention else "failed",
        "command_id": command_id,
        "reply": reply,
        "capability": command.get("capability"),
        "provider_id": execution.provider_id,
        "execution_status": execution.status,
    }
    event = event_base(raw_text, phrase, was_off_record, by_id)
    event.update({
        "matched_command_id": command_id, "matched_alias": alias,
        "result": result["status"], "clarification_count": clarification_count,
        "action": action, "execution_status": execution.status,
        "capability": command.get("capability"), "provider_id": execution.provider_id,
        "execution_detail": execution.detail,
        "duration_ms": round((time.monotonic() - started) * 1000),
    })
    log_event(event, was_off_record)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Route one ArCHi command without AI.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--silent", action="store_true", help="Record a silent/no-transcript control event.")
    args = parser.parse_args()
    if args.list:
        _, by_id = load_commands()
        for command_id in by_id:
            print(command_id)
        return 0
    if args.silent:
        result = record_silent(dry_run=args.dry_run)
        if args.dry_run:
            print(json.dumps(result))
        return 0
    result = route(sys.stdin.read(), dry_run=args.dry_run)
    if args.dry_run:
        print(json.dumps(result))
    return 0 if result["status"] != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
