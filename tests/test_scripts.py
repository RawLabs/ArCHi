import json
import os
from pathlib import Path
import subprocess
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def write_executable(path: Path, contents: str) -> None:
    path.write_text(contents)
    path.chmod(0o755)


def test_installer_preserves_registry_and_can_refresh_it(tmp_path):
    bin_dir = tmp_path / "bin"
    archi_home = tmp_path / "share" / "archi"
    archi_home.mkdir(parents=True)
    (archi_home / "savvy.wav").write_bytes(b"private voice sample")
    env = {
        **os.environ,
        "ARCHI_BIN_DIR": str(bin_dir),
        "ARCHI_HOME": str(archi_home),
    }

    subprocess.run([PROJECT_ROOT / "install.sh"], env=env, check=True)
    active_registry = archi_home / "commands.toml"
    default_registry = archi_home / "commands.default.toml"
    project_registry = (PROJECT_ROOT / "config" / "commands.toml").read_text()
    project_intents = (PROJECT_ROOT / "config" / "intents.yaml").read_text()
    assert active_registry.read_text() == project_registry
    assert default_registry.read_text() == project_registry
    assert (archi_home / "intents.yaml").read_text() == project_intents
    migrated_voice = archi_home / "assets" / "voice.wav"
    assert migrated_voice.read_bytes() == b"private voice sample"
    assert migrated_voice.stat().st_mode & 0o777 == 0o600

    active_registry.write_text("# local customization\n")
    subprocess.run([PROJECT_ROOT / "install.sh"], env=env, check=True)
    assert active_registry.read_text() == "# local customization\n"
    assert default_registry.read_text() == project_registry

    subprocess.run(
        [PROJECT_ROOT / "install.sh", "--refresh-registry"], env=env, check=True
    )
    assert active_registry.read_text() == project_registry
    backups = list(archi_home.glob("commands.toml.bak.*"))
    assert len(backups) == 1
    assert backups[0].read_text() == "# local customization\n"


def test_shadow_report_summarizes_coverage_and_review_queue(tmp_path):
    log_path = tmp_path / "commands.jsonl"
    registry_path = tmp_path / "commands.toml"
    registry_path.write_text(
        '[[commands]]\nid = "open_browser"\naction = "launch"\n'
        '[[commands]]\nid = "open_terminal"\naction = "launch"\n'
    )
    events = [
        {
            "result": "success",
            "matched_command_id": "open_browser",
            "normalized_phrase": "open browser",
            "performance": {"on_ac_power": True},
            "shadow": {"status": "matched", "command_id": "open_browser", "duration_ms": 12},
            "comparison": "agree",
        },
        {
            "result": "unknown",
            "matched_command_id": None,
            "normalized_phrase": "launch console",
            "performance": {"on_ac_power": False},
            "shadow": {"status": "matched", "command_id": "open_terminal", "duration_ms": 14},
            "comparison": "shadow_extension",
        },
    ]
    log_path.write_text("".join(f"{json.dumps(event)}\n" for event in events))

    result = subprocess.run(
        [
            sys.executable,
            PROJECT_ROOT / "scripts" / "archi-shadow-report",
            "--log",
            log_path,
            "--registry",
            registry_path,
            "--details",
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    assert "comparison: agree=1, shadow_extension=1" in result.stdout
    assert "production command coverage: 1/2" in result.stdout
    assert "review queue: 1" in result.stdout
    assert "shadow_extension\t-\topen_terminal\tlaunch console" in result.stdout


def test_control_stop_bounds_missing_transcript_wait(tmp_path):
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    voxtype = fake_bin / "voxtype"
    write_executable(voxtype, "#!/usr/bin/env bash\nexit 0\n")

    archi_home = tmp_path / "share" / "archi"
    archi_home.mkdir(parents=True)
    marker = tmp_path / "router-call"
    router_stub = archi_home / "router.py"
    router_stub.write_text(
        "import os, pathlib, sys\n"
        "pathlib.Path(os.environ['ARCHI_TEST_MARKER']).write_text("
        "os.environ.get('ARCHI_SESSION_ID', '') + ' ' + ' '.join(sys.argv[1:]))\n"
    )

    runtime_root = tmp_path / "runtime"
    runtime_dir = runtime_root / "archi"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "control-session-id").write_text("test-session")
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "ARCHI_HOME": str(archi_home),
        "ARCHI_TEST_MARKER": str(marker),
        "ARCHI_TRANSCRIPT_WAIT_TICKS": "1",
        "XDG_RUNTIME_DIR": str(runtime_root),
    }

    started = time.monotonic()
    subprocess.run([PROJECT_ROOT / "scripts" / "archi-control-stop"], env=env, check=True)
    elapsed = time.monotonic() - started

    assert elapsed < 1
    assert marker.read_text() == "test-session --silent"
    assert not (runtime_dir / "control-session-id").exists()


def test_control_cancel_removes_all_session_files(tmp_path):
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    voxtype = fake_bin / "voxtype"
    write_executable(voxtype, "#!/usr/bin/env bash\nexit 0\n")

    runtime_root = tmp_path / "runtime"
    runtime_dir = runtime_root / "archi"
    runtime_dir.mkdir(parents=True)
    transcript = runtime_dir / "control-transcript.txt"
    session = runtime_dir / "control-session-id"
    start_time = runtime_dir / "control-start-ns"
    transcript.write_text("unused")
    session.write_text("unused")
    start_time.write_text("100")
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "XDG_RUNTIME_DIR": str(runtime_root),
    }

    subprocess.run([PROJECT_ROOT / "scripts" / "archi-control-cancel"], env=env, check=True)

    assert not transcript.exists()
    assert not session.exists()
    assert not start_time.exists()


def test_tts_uses_bounded_request_and_safe_volume_default(tmp_path):
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    curl_marker = tmp_path / "curl-args"
    player_marker = tmp_path / "player-args"
    write_executable(
        fake_bin / "curl",
        """#!/usr/bin/env bash
printf '%s\n' "$@" > "$ARCHI_TEST_CURL_MARKER"
while (($#)); do
  if [[ "$1" == "--output" ]]; then
    shift
    printf 'RIFF' > "$1"
    exit 0
  fi
  shift
done
exit 2
""",
    )
    write_executable(fake_bin / "pw-dump", "#!/usr/bin/env bash\nprintf '[]\\n'\n")
    write_executable(
        fake_bin / "pw-play",
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" > \"$ARCHI_TEST_PLAYER_MARKER\"\n",
    )

    runtime_root = tmp_path / "runtime"
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "ARCHI_TEST_CURL_MARKER": str(curl_marker),
        "ARCHI_TEST_PLAYER_MARKER": str(player_marker),
        "POCKET_TTS_TIMEOUT_SECONDS": "2",
        "POCKET_TTS_VOLUME": "not-a-number",
        "XDG_RUNTIME_DIR": str(runtime_root),
    }

    subprocess.run(
        [PROJECT_ROOT / "scripts" / "pocket-tts-say"],
        input="A short test.",
        text=True,
        env=env,
        check=True,
    )

    curl_args = curl_marker.read_text().splitlines()
    player_args = player_marker.read_text().splitlines()
    assert curl_args[curl_args.index("--max-time") + 1] == "2"
    assert curl_args[curl_args.index("--connect-timeout") + 1] == "2"
    assert player_args[player_args.index("--volume") + 1] == "1.0"
    assert not (runtime_root / "archi" / "pocket-tts-player.pid").exists()


def test_clipboard_reader_snapshots_text_and_logs_only_metadata(tmp_path):
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    spoken = tmp_path / "spoken-text"
    write_executable(
        fake_bin / "wl-paste",
        "#!/usr/bin/env bash\nprintf 'clipboard sample'\n",
    )
    write_executable(
        fake_bin / "pocket-tts-say",
        "#!/usr/bin/env bash\ncat > \"$ARCHI_TEST_SPOKEN\"\n",
    )
    state_root = tmp_path / "state"
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "ARCHI_BIN_DIR": str(fake_bin),
        "ARCHI_TEST_SPOKEN": str(spoken),
        "XDG_STATE_HOME": str(state_root),
    }

    subprocess.run(
        [PROJECT_ROOT / "scripts" / "pocket-tts-read-clipboard"],
        env=env,
        check=True,
    )

    assert spoken.read_text() == "clipboard sample"
    log_path = state_root / "archi" / "clipboard.jsonl"
    event = json.loads(log_path.read_text())
    assert event["bytes"] == len(b"clipboard sample")
    assert len(event["sha256"]) == 64
    assert event["status"] == "spoken"
    assert "clipboard sample" not in log_path.read_text()
    assert log_path.stat().st_mode & 0o777 == 0o600
