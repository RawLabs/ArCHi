import json
import os
from pathlib import Path

import pytest

from archi import router
from archi.adapters.base import ActionResult
from archi.adapters.omarchy import OmarchyDesktopAdapter


@pytest.fixture(autouse=True)
def isolated_app_registry(monkeypatch, tmp_path):
    applications = tmp_path / "applications"
    applications.mkdir()
    (applications / "cliamp.desktop").write_text(
        """[Desktop Entry]
Type=Application
Name=cliamp
GenericName=Music Player
Exec=cliamp
Terminal=true
"""
    )
    monkeypatch.setenv("ARCHI_APPLICATION_DIRS", str(applications))
    monkeypatch.setenv("ARCHI_APP_ALIASES_PATH", str(tmp_path / "app-aliases.toml"))
    return applications


@pytest.fixture
def isolated_router(monkeypatch, tmp_path):
    runtime_dir = tmp_path / "runtime" / "archi"
    log_path = tmp_path / "state" / "commands.jsonl"
    monkeypatch.setattr(router, "RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr(router, "OFF_RECORD_PATH", runtime_dir / "off-record")
    monkeypatch.setattr(router, "PENDING_PATH", runtime_dir / "pending.json")
    monkeypatch.setattr(router, "ADJUSTMENT_PATH", runtime_dir / "adjustment.json")
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


def test_normalize_removes_verbal_stop_terminator():
    assert router.normalize("open terminal, ArCHi stop") == "open terminal"
    assert router.normalize("ArChie, stop") == ""


def test_verbal_stop_without_a_command_is_silent(isolated_router):
    result = router.route("ArChI stop", dry_run=True)
    assert result == {"status": "silent", "reason": "empty_command"}
    assert read_events(isolated_router)[0]["silent_reason"] == "empty_command"


def test_registry_loads():
    by_phrase, by_id = router.load_commands()
    assert by_phrase["open cliamp"]["id"] == "open_app:cliamp.desktop"
    assert by_phrase["close cliamp"]["id"] == "close_app:cliamp.desktop"
    assert by_phrase["open music player"]["capability"] == "app.open"
    assert by_phrase["open music player"]["payload"]["launcher_id"] == "cliamp"
    assert by_phrase["close home"]["id"] == "close_home"
    assert by_phrase["close downloads"]["id"] == "close_downloads"
    assert by_phrase["mute"]["id"] == "mute"
    assert by_phrase["unmute"]["id"] == "unmute"
    assert by_phrase["turn volume on"]["id"] == "unmute"
    assert by_phrase["toggle mute"]["id"] == "toggle_mute"
    assert "identity" in by_id
    assert set(command["action"] for command in by_id.values()) <= {
        "clarify",
        "capability",
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
        if command["action"] == "capability":
            assert command.get("capability")
            assert "argv" not in command


def test_open_commands_have_matching_close_commands():
    _, by_id = router.load_commands()
    app_ids = {command["desktop_id"] for command in by_id.values() if command.get("desktop_id")}
    for desktop_id in app_ids:
        assert f"open_app:{desktop_id}" in by_id
        assert f"close_app:{desktop_id}" in by_id


def test_desktop_registry_refreshes_on_each_load(isolated_app_registry):
    by_phrase, _ = router.load_commands()
    assert "open fresh app" not in by_phrase

    (isolated_app_registry / "fresh.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Fresh App\nExec=fresh-app\n"
    )
    by_phrase, _ = router.load_commands()
    assert by_phrase["open fresh app"]["payload"]["launcher_id"] == "fresh"
    assert by_phrase["close fresh app"]["capability"] == "app.close"


def test_user_spoken_alias_routes_only_to_its_currently_installed_app(monkeypatch, isolated_app_registry, tmp_path):
    alias_path = tmp_path / "app-aliases.toml"
    alias_path.write_text(
        '[[aliases]]\ndesktop_id = "cliamp.desktop"\nphrase = "cli amp right"\n'
    )
    monkeypatch.setenv("ARCHI_APP_ALIASES_PATH", str(alias_path))

    by_phrase, _ = router.load_commands()

    assert by_phrase["close cli amp right"]["id"] == "close_app:cliamp.desktop"


def test_user_spoken_alias_does_not_route_when_its_app_is_not_installed(monkeypatch, tmp_path):
    applications = tmp_path / "applications"
    applications.mkdir(exist_ok=True)
    monkeypatch.setenv("ARCHI_APPLICATION_DIRS", str(applications))
    alias_path = tmp_path / "app-aliases.toml"
    alias_path.write_text(
        '[[aliases]]\ndesktop_id = "missing.desktop"\nphrase = "missing app"\n'
    )
    monkeypatch.setenv("ARCHI_APP_ALIASES_PATH", str(alias_path))

    by_phrase, _ = router.load_commands()

    assert "close missing app" not in by_phrase


def test_hidden_user_entry_suppresses_same_system_app(monkeypatch, tmp_path):
    user_apps = tmp_path / "user"
    system_apps = tmp_path / "system"
    user_apps.mkdir()
    system_apps.mkdir()
    (user_apps / "hidden.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Hidden App\nHidden=true\n"
    )
    (system_apps / "hidden.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Hidden App\nExec=hidden-app\n"
    )
    monkeypatch.setenv("ARCHI_APPLICATION_DIRS", f"{user_apps}{os.pathsep}{system_apps}")
    by_phrase, _ = router.load_commands()
    assert "open hidden app" not in by_phrase


def test_shared_app_alias_is_not_routed_ambiguously(isolated_app_registry):
    (isolated_app_registry / "other.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Other Player\nGenericName=Music Player\nExec=other\n"
    )
    by_phrase, _ = router.load_commands()
    assert "open music player" not in by_phrase
    assert by_phrase["open cliamp"]["desktop_id"] == "cliamp.desktop"


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


def test_capture_context_validates_wrapper_timings(monkeypatch):
    monkeypatch.setenv("ARCHI_CAPTURE_DURATION_MS", "1420")
    monkeypatch.setenv("ARCHI_TRANSCRIPT_WAIT_MS", "not-a-number")
    assert router.capture_context() == {
        "session_duration_ms": 1420,
        "transcript_wait_ms": None,
    }


def test_successful_route_is_logged(isolated_router):
    result = router.route("ArCHi, can you open cliamp?", dry_run=True)
    assert result["status"] == "success"
    assert result["command_id"] == "open_app:cliamp.desktop"

    events = read_events(isolated_router)
    assert len(events) == 1
    assert events[0]["transcript"] == "ArCHi, can you open cliamp?"
    assert events[0]["normalized_phrase"] == "open cliamp"
    assert events[0]["matched_command_id"] == "open_app:cliamp.desktop"
    assert events[0]["execution_status"] == "success"
    assert events[0]["schema_version"] == router.SCHEMA_VERSION
    assert os.stat(isolated_router).st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    ("phrase", "command_id"),
    [
        ("open c l i a m p", "open_app:cliamp.desktop"),
        ("close c l i a m p", "close_app:cliamp.desktop"),
        ("openclamp", "open_app:cliamp.desktop"),
        ("closeclimp", "close_app:cliamp.desktop"),
    ],
)
def test_dynamic_app_matching_accepts_spaced_letters_and_small_transcription_errors(
    isolated_router, phrase, command_id
):
    result = router.route(phrase, dry_run=True)
    assert result["status"] == "success"
    assert result["command_id"] == command_id
    assert read_events(isolated_router)[0]["matched_alias"] == "cliamp"


def test_dynamic_app_matching_treats_q_c_and_k_as_phonetic_equivalents(isolated_app_registry, isolated_router):
    (isolated_app_registry / "qamera.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Qamera\nExec=qamera\n"
    )

    result = router.route("open kamera", dry_run=True)
    assert result["status"] == "success"
    assert result["command_id"] == "open_app:qamera.desktop"


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


def test_route_reports_heard_and_success_feedback(isolated_router, monkeypatch):
    events = []
    monkeypatch.setattr(router, "show_feedback", lambda *args: events.append(args))
    monkeypatch.setattr(
        router,
        "execute",
        lambda command, _dry_run: ActionResult("success", "test", command.get("capability", "test")),
    )

    result = router.route("open cliamp", dry_run=False)

    assert result["status"] == "success"
    assert events == [
        ("heard", "Heard: open cliamp", 1000, False),
        ("success", "Opening cliamp.", 1300, False),
    ]


def test_zoom_followups_and_cancel_restore_original_factor(isolated_router, monkeypatch):
    actions = []
    monkeypatch.setattr(router, "current_zoom_factor", lambda: 1.5)
    monkeypatch.setattr(
        router, "execute",
        lambda command, _dry_run: (
            actions.append((command["id"], command.get("payload")))
            or ActionResult("success", "test", command.get("capability", "test"))
        ),
    )

    assert router.route("ArCHi, zoom")["command_id"] == "zoom_in"
    assert router.route("more")["command_id"] == "zoom_in"
    assert router.route("a little less")["command_id"] == "zoom_less"
    cancelled = router.route("cancel")
    assert cancelled["command_id"] == "zoom_restore"
    assert cancelled["status"] == "cancelled"
    assert actions[-1] == ("zoom_restore", {"factor": 1.5})
    assert not router.ADJUSTMENT_PATH.exists()
    assert router.route("more")["status"] == "unknown"
    assert len(actions) == 4


def test_zoom_out_resets_and_clears_followup_context(isolated_router, monkeypatch):
    actions = []
    monkeypatch.setattr(router, "current_zoom_factor", lambda: 1.0)
    monkeypatch.setattr(
        router, "execute",
        lambda command, _dry_run: (
            actions.append(command["id"])
            or ActionResult("success", "test", command.get("capability", "test"))
        ),
    )
    router.route("make the screen bigger")
    assert router.route("zoom out")["command_id"] == "zoom_out"
    assert router.route("less")["status"] == "unknown"
    assert actions == ["zoom_in", "zoom_out"]


def test_cancel_preserves_zoom_changed_outside_archi(isolated_router, monkeypatch):
    factor = 1.0
    actions = []
    monkeypatch.setattr(router, "current_zoom_factor", lambda: factor)

    def fake_execute(command, _dry_run):
        nonlocal factor
        actions.append(command["id"])
        if command["id"] == "zoom_in":
            factor += 1.0
        return ActionResult("success", "test", command.get("capability", "test"))

    monkeypatch.setattr(router, "execute", fake_execute)
    router.route("zoom")
    factor = 3.0  # A keyboard binding or another controller changed zoom.
    result = router.route("cancel")
    assert result["status"] == "cancelled"
    assert "left it" in result["reply"]
    assert factor == 3.0
    assert actions == ["zoom_in"]


def test_volume_followups_do_not_change_zoom(isolated_router, monkeypatch):
    actions = []
    monkeypatch.setattr(
        router, "execute",
        lambda command, _dry_run: (
            actions.append(command["id"])
            or ActionResult("success", "test", command.get("capability", "test"))
        ),
    )
    router.route("raise the volume")
    assert router.route("more")["command_id"] == "volume_up"
    assert router.route("less")["command_id"] == "volume_down"
    assert router.route("cancel")["status"] == "cancelled"
    assert router.route("more")["status"] == "unknown"
    assert actions == ["volume_up", "volume_up", "volume_down"]


def test_feedback_phrase_limits_long_transcripts():
    phrase = "a" * 81
    assert router.feedback_phrase(phrase) == f"{'a' * 77}..."


def test_clarification_routes_only_an_allowlisted_target(isolated_router, monkeypatch):
    executed_ids = []
    monkeypatch.setattr(
        router,
        "execute",
        lambda command, _dry_run: (
            executed_ids.append(command["id"])
            or ActionResult("success", "test", command.get("capability", "test"))
        ),
    )

    first = router.route("close")
    assert first["status"] == "clarifying"
    assert router.PENDING_PATH.exists()

    second = router.route("home")
    assert second["status"] == "success"
    assert second["command_id"] == "close_home"
    assert executed_ids == ["close_home"]
    assert not router.PENDING_PATH.exists()
    assert read_events(isolated_router)[1]["clarification_count"] == 1


def test_off_record_suppresses_events_until_logging_resumes(isolated_router, monkeypatch):
    monkeypatch.setattr(
        router,
        "execute",
        lambda command, _dry_run: ActionResult("success", "test", command.get("capability", "test")),
    )

    assert router.route("off record")["status"] == "off_record"
    assert router.OFF_RECORD_PATH.exists()
    assert router.route("open cliamp")["status"] == "success"
    assert read_events(isolated_router) == []

    assert router.route("logging on")["status"] == "logging_on"
    assert not router.OFF_RECORD_PATH.exists()
    assert router.route("open cliamp")["status"] == "success"
    assert len(read_events(isolated_router)) == 1


def test_silent_input_is_recorded(isolated_router):
    result = router.record_silent()
    assert result == {"status": "silent", "reason": "no_transcript"}
    event = read_events(isolated_router)[0]
    assert event["event_type"] == "silent_input"
    assert event["result"] == "silent"
    assert event["shadow"]["status"] == "test"
    assert event["comparison"] == "not_comparable"


@pytest.mark.parametrize(
    ("production_id", "shadow_status", "shadow_id", "expected"),
    [
        ("volume_up", "matched", "volume_up", "agree"),
        (None, "no_match", None, "agree"),
        (None, "matched", "volume_up", "shadow_extension"),
        ("volume_up", "no_match", None, "shadow_regression"),
        ("volume_up", "matched", "volume_down", "conflict"),
        ("volume_up", "not_installed", None, "not_comparable"),
    ],
)
def test_shadow_comparison_labels(production_id, shadow_status, shadow_id, expected):
    event = {
        "event_type": "command",
        "matched_command_id": production_id,
        "shadow": {"status": shadow_status, "command_id": shadow_id},
    }
    assert router.classify_shadow(event) == expected


def test_clarification_answer_is_not_compared_without_shadow_context():
    event = {
        "event_type": "command",
        "matched_command_id": "close_home",
        "clarification_count": 1,
        "shadow": {"status": "no_match"},
    }
    assert router.classify_shadow(event) == "not_comparable"


def test_independent_hassil_grammar_covers_exact_registry():
    by_phrase, by_id = router.load_commands()
    first = router.hassil_shadow("volume up", by_id)
    if first["status"] == "not_installed":
        pytest.skip("optional HassIL dependency is not installed")

    failures = []
    for phrase, command in by_phrase.items():
        if command.get("desktop_id"):
            continue
        shadow = router.hassil_shadow(phrase, by_id)
        if shadow.get("status") != "matched" or shadow.get("command_id") != command["id"]:
            failures.append((phrase, command["id"], shadow))
    assert failures == []


def test_independent_hassil_grammar_finds_natural_extensions():
    _, by_id = router.load_commands()
    shadow = router.hassil_shadow("raise the volume", by_id)
    if shadow["status"] == "not_installed":
        pytest.skip("optional HassIL dependency is not installed")
    assert shadow["status"] == "matched"
    assert shadow["command_id"] == "volume_up"


def test_dynamic_apps_are_skipped_by_static_shadow_grammar():
    _, by_id = router.load_commands()
    assert router.hassil_shadow("open cliamp", by_id)["reason"] == "dynamic_app_registry"


def test_unknown_action_never_executes():
    assert router.execute({"action": "not_allowed", "argv": ["true"]}, dry_run=False).status == "unsupported"


def test_omarchy_zoom_uses_native_cursor_setting_and_validates_restore(monkeypatch, tmp_path):
    calls = []
    factor = 1.5

    def fake_run(argv, **_kwargs):
        nonlocal factor
        calls.append(argv)
        if argv == ["hyprctl", "-j", "getoption", "cursor.zoom_factor"]:
            return type("Result", (), {"returncode": 0, "stdout": json.dumps({"float": factor}), "stderr": ""})()
        if argv[:2] == ["hyprctl", "eval"]:
            factor = float(argv[2].split("zoom_factor = ", 1)[1].split(" ", 1)[0])
            return type("Result", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()
        raise AssertionError(argv)

    monkeypatch.setattr("archi.adapters.omarchy.subprocess.run", fake_run)
    adapter = OmarchyDesktopAdapter(tmp_path)
    assert adapter.execute("visual.zoom.in", {}).succeeded
    assert factor == 2.5
    assert adapter.execute("visual.zoom.out", {}).succeeded
    assert factor == 1.5
    assert adapter.execute("visual.zoom.restore", {"factor": 1.25}).succeeded
    assert factor == 1.25
    assert adapter.execute("visual.zoom.restore", {"factor": 99}).status == "failed"
    assert adapter.execute("visual.zoom.reset", {}).succeeded
    assert factor == 1.0
    assert ["hyprctl", "eval", "hl.config({ cursor = { zoom_factor = 1 } })"] in calls
    calls_before = len(calls)
    assert adapter.execute("visual.zoom.out", {}).detail == "zoom already at requested level"
    assert len(calls) == calls_before + 1  # Read-only state check; no config write.


def test_omarchy_adapter_closes_matching_window_address(monkeypatch, tmp_path):
    calls = []
    client_reads = 0

    def fake_run(argv, **_kwargs):
        nonlocal client_reads
        calls.append(argv)
        if argv == ["hyprctl", "-j", "clients"]:
            client_reads += 1
            clients = [
                {"address": "0x1", "class": "foot", "initialClass": "foot", "title": "shell", "focusHistoryID": 0},
                {"address": "0x2", "class": "foot", "initialClass": "foot", "title": "cliamp", "focusHistoryID": 1},
            ] if client_reads == 1 else [
                {"address": "0x1", "class": "foot", "initialClass": "foot", "title": "shell", "focusHistoryID": 0},
            ]
            return type("Result", (), {
                "returncode": 0,
                "stdout": json.dumps(clients),
            })()
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr("archi.adapters.omarchy.subprocess.run", fake_run)
    command = router.dynamic_app_commands()[1]
    assert command["id"] == "close_app:cliamp.desktop"
    adapter = OmarchyDesktopAdapter(tmp_path)
    result = adapter.execute(command["capability"], command["payload"])
    assert result.status == "success"
    assert [
        "hyprctl",
        "dispatch",
        'hl.dsp.window.close({ window = "address:0x2" })',
    ] in calls
    assert ["hyprctl", "-j", "activeworkspace"] not in calls


def test_omarchy_adapter_flags_background_window_that_needs_attention(monkeypatch, tmp_path):
    calls = []

    def fake_run(argv, **_kwargs):
        calls.append(argv)
        if argv == ["hyprctl", "-j", "clients"]:
            return type("Result", (), {
                "returncode": 0,
                "stdout": json.dumps([
                    {"address": "0x2", "class": "foot", "initialClass": "foot", "title": "cliamp", "focusHistoryID": 1},
                ]),
            })()
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr("archi.adapters.omarchy.subprocess.run", fake_run)
    monkeypatch.setattr(OmarchyDesktopAdapter, "_CLOSE_CONFIRM_DELAY_SECONDS", 0)
    command = router.dynamic_app_commands()[1]
    adapter = OmarchyDesktopAdapter(tmp_path)
    result = adapter.execute(command["capability"], command["payload"])

    assert result.status == "attention"
    assert "needs attention" in (result.detail or "")
    assert ["hyprctl", "-j", "activeworkspace"] not in calls
    assert ["hyprctl", "dispatch", 'hl.dsp.window.close({ window = "address:0x2" })'] in calls


def test_route_reports_attention_without_claiming_an_app_closed(isolated_router, monkeypatch):
    feedback = []
    monkeypatch.setattr(
        router,
        "execute",
        lambda _command, _dry_run: ActionResult("attention", "test", "app.close", "window remains"),
    )
    monkeypatch.setattr(router, "show_feedback", lambda *args: feedback.append(args))

    result = router.route("close cliamp")

    assert result["status"] == "attention"
    assert result["reply"] == "cliamp needs attention."
    assert result["execution_status"] == "attention"
    assert ("attention", "cliamp needs attention.", 3500, False) in feedback
    assert feedback[-1][0] == "attention"


def test_omarchy_feedback_uses_transient_osd_not_system_notifications(monkeypatch, tmp_path):
    calls = []
    monkeypatch.delenv("ARCHI_FEEDBACK", raising=False)
    monkeypatch.setattr(
        "archi.adapters.omarchy.subprocess.Popen",
        lambda argv, **kwargs: calls.append((argv, kwargs)),
    )

    OmarchyDesktopAdapter(tmp_path).feedback("heard", "Heard: open cliamp", 1000)

    assert calls == [(
        [
            "omarchy-osd",
            "--icon", "microphone",
            "--message", "Heard: open cliamp",
            "--duration", "1000",
        ],
        {"start_new_session": True, "stdout": -3, "stderr": -3},
    )]


def test_dry_run_reports_selected_adapter_without_execution(monkeypatch):
    class StubAdapter:
        provider_id = "test.desktop"

        def capabilities(self):
            return frozenset({"app.open"})

    monkeypatch.setattr(router, "select_desktop_adapter", lambda _path: StubAdapter())
    result = router.execute(
        {"action": "capability", "capability": "app.open", "payload": {}},
        dry_run=True,
    )
    assert result == ActionResult("success", "test.desktop", "app.open")


def test_unknown_desktop_adapter_is_unavailable(monkeypatch):
    monkeypatch.setenv("ARCHI_DESKTOP_ADAPTER", "not-a-real-adapter")
    result = router.execute(
        {"action": "capability", "capability": "app.open", "payload": {}},
        dry_run=True,
    )
    assert result.status == "unavailable"
    assert result.provider_id == "none"


@pytest.mark.parametrize("state", [[], None, {"expires": "later"}, {"expires": float("nan")}, {"expires": 1e20, "command_id": "close", "targets": []}])
def test_invalid_pending_state_is_ignored(isolated_router, state):
    router.RUNTIME_DIR.mkdir(parents=True)
    router.PENDING_PATH.write_text(json.dumps(state))
    assert router.route("who are you", dry_run=True)["status"] == "success"


def test_dry_run_keeps_pending_confirmation(isolated_router, monkeypatch):
    monkeypatch.setattr(router, "execute", lambda *_args: ActionResult("success", "test", "folder.close"))
    router.route("close")
    original = router.PENDING_PATH.read_bytes()
    router.route("cancel", dry_run=True)
    assert router.PENDING_PATH.read_bytes() == original
    router.route("home", dry_run=True)
    assert router.PENDING_PATH.read_bytes() == original


def test_new_command_invalidates_old_confirmation(isolated_router, monkeypatch):
    monkeypatch.setattr(router, "execute", lambda *_args: ActionResult("success", "test", "test"))
    router.route("close")
    router.route("volume up")
    assert not router.PENDING_PATH.exists()
    assert router.route("home")["status"] == "unknown"


def test_old_registry_without_zoom_commands_does_not_crash_followup(isolated_router, monkeypatch):
    router.save_adjustment("zoom", 1.0, 2.0)
    monkeypatch.setattr(router, "load_commands", lambda: ({}, {}))
    assert router.route("more", dry_run=True)["status"] == "unknown"
    assert router.route("cancel", dry_run=True)["status"] == "unknown"


def test_missing_speech_helper_is_reported_without_crash(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(router, "SPEAK", str(tmp_path / "missing-helper"))
    router.speak("Test", False)
    assert "speech unavailable" in capsys.readouterr().err


def test_unwritable_log_does_not_crash_completed_command(isolated_router, monkeypatch, tmp_path, capsys):
    blocker = tmp_path / "file-not-directory"
    blocker.write_text("blocked")
    monkeypatch.setattr(router, "LOG_PATH", blocker / "commands.jsonl")
    assert router.route("who are you", dry_run=True)["status"] == "success"
    assert "diagnostic log unavailable" in capsys.readouterr().err


def test_gui_app_close_uses_class_not_another_apps_document_title():
    payload = {"desktop_id": "editor.desktop", "app_name": "Editor", "executable": "editor"}
    browser = {"class": "browser", "title": "Editor documentation", "focusHistoryID": 0}
    editor = {"class": "editor", "title": "notes.txt", "focusHistoryID": 1}
    assert OmarchyDesktopAdapter._best_window_match([browser, editor], payload) == editor
    assert OmarchyDesktopAdapter._best_window_match([browser], payload) is None


def test_terminal_app_title_must_belong_to_a_terminal():
    payload = {"desktop_id": "cliamp.desktop", "app_name": "cliamp", "terminal": True}
    browser = {"class": "browser", "title": "cliamp documentation", "focusHistoryID": 0}
    terminal = {"class": "foot", "title": "cliamp", "focusHistoryID": 1}
    assert OmarchyDesktopAdapter._best_window_match([browser, terminal], payload) == terminal
    assert OmarchyDesktopAdapter._best_window_match([browser], payload) is None


def test_invalid_adjustment_family_does_not_crash(isolated_router):
    router.RUNTIME_DIR.mkdir(parents=True)
    router.ADJUSTMENT_PATH.write_text('{"family": [], "expires": 1e20}')
    assert router.route("more", dry_run=True)["status"] == "unknown"
