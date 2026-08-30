import json
import os
from pathlib import Path

import pytest

from archi import router


@pytest.fixture
def isolated_router(monkeypatch, tmp_path):
    runtime_dir = tmp_path / "runtime" / "archi"
    log_path = tmp_path / "state" / "commands.jsonl"
    monkeypatch.setattr(router, "RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr(router, "OFF_RECORD_PATH", runtime_dir / "off-record")
    monkeypatch.setattr(router, "PENDING_PATH", runtime_dir / "pending.json")
    monkeypatch.setattr(router, "LOG_PATH", log_path)
    monkeypatch.setattr(router, "speak", lambda _text, _dry_run: None)
    monkeypatch.setattr(router, "desktop_context", lambda: {"capture_status": "test"})
    monkeypatch.setattr(router, "performance_context", lambda: {"capture_status": "test"})
    monkeypatch.setattr(
        router,
        "hassil_shadow",
        lambda phrase, _commands: {"parser": "hassil", "status": "test", "phrase": phrase},
    )
    return log_path


def read_events(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    return [json.loads(line) for line in log_path.read_text().splitlines()]


def test_normalize_removes_archi_name_and_politeness():
    assert router.normalize("ArCHi, please open terminal") == "open terminal"
    assert router.normalize("archie volume up") == "volume up"


def test_registry_loads():
    by_phrase, by_id = router.load_commands()
    assert by_phrase["open terminal"]["id"] == "open_terminal"
    assert "identity" in by_id
    assert set(command["action"] for command in by_id.values()) <= {
        "clarify",
        "launch",
        "mode_logging_on",
        "mode_off_record",
        "reply",
        "run",
    }
    for command in by_id.values():
        if command["action"] in {"launch", "run"}:
            assert command.get("argv")
            assert all(isinstance(argument, str) for argument in command["argv"])


def test_duplicate_registry_phrase_is_rejected(monkeypatch, tmp_path):
    registry = tmp_path / "commands.toml"
    registry.write_text(
        """
[[commands]]
id = "one"
phrases = ["same phrase"]
action = "reply"
reply = "One"

[[commands]]
id = "two"
phrases = ["same phrase"]
action = "reply"
reply = "Two"
""".strip()
    )
    monkeypatch.setattr(router, "REGISTRY_PATH", registry)
    with pytest.raises(ValueError, match="duplicate command phrase"):
        router.load_commands()


def test_argv_expansion_is_portable(monkeypatch):
    monkeypatch.setattr(router, "ARCHI_BIN_DIR", Path("/tmp/archi-bin"))
    assert router.expand_argv(["{home}/Downloads", "{archi_bin}/archi-stop-speaking"]) == [
        f"{Path.home()}/Downloads",
        "/tmp/archi-bin/archi-stop-speaking",
    ]


def test_successful_route_is_logged(isolated_router):
    result = router.route("ArCHi, can you open terminal?", dry_run=True)
    assert result["status"] == "success"
    assert result["command_id"] == "open_terminal"

    events = read_events(isolated_router)
    assert len(events) == 1
    assert events[0]["transcript"] == "ArCHi, can you open terminal?"
    assert events[0]["normalized_phrase"] == "open terminal"
    assert events[0]["matched_command_id"] == "open_terminal"
    assert events[0]["execution_status"] == "success"
    assert events[0]["schema_version"] == router.SCHEMA_VERSION
    assert os.stat(isolated_router).st_mode & 0o777 == 0o600


def test_unknown_route_is_logged_without_execution(isolated_router, monkeypatch):
    executed = False

    def unexpected_execute(_command, _dry_run):
        nonlocal executed
        executed = True
        return True

    monkeypatch.setattr(router, "execute", unexpected_execute)
    result = router.route("open bananas")
    assert result["status"] == "unknown"
    assert executed is False
    assert read_events(isolated_router)[0]["execution_status"] == "not_run"


def test_clarification_routes_only_an_allowlisted_target(isolated_router, monkeypatch):
    executed_ids = []
    monkeypatch.setattr(
        router,
        "execute",
        lambda command, _dry_run: not executed_ids.append(command["id"]),
    )

    first = router.route("close")
    assert first["status"] == "clarifying"
    assert router.PENDING_PATH.exists()

    second = router.route("terminal")
    assert second["status"] == "success"
    assert second["command_id"] == "close_terminal"
    assert executed_ids == ["close_terminal"]
    assert not router.PENDING_PATH.exists()
    assert read_events(isolated_router)[1]["clarification_count"] == 1


def test_off_record_suppresses_events_until_logging_resumes(isolated_router, monkeypatch):
    monkeypatch.setattr(router, "execute", lambda _command, _dry_run: True)

    assert router.route("off record")["status"] == "off_record"
    assert router.OFF_RECORD_PATH.exists()
    assert router.route("open terminal")["status"] == "success"
    assert read_events(isolated_router) == []

    assert router.route("logging on")["status"] == "logging_on"
    assert not router.OFF_RECORD_PATH.exists()
    assert router.route("open terminal")["status"] == "success"
    assert len(read_events(isolated_router)) == 1


def test_silent_input_is_recorded(isolated_router):
    result = router.record_silent()
    assert result == {"status": "silent", "reason": "no_transcript"}
    event = read_events(isolated_router)[0]
    assert event["event_type"] == "silent_input"
    assert event["result"] == "silent"
    assert event["shadow"]["status"] == "test"


def test_unknown_action_never_executes():
    assert router.execute({"action": "not_allowed", "argv": ["true"]}, dry_run=False) is False
