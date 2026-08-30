from pathlib import Path

from archi import router


def test_normalize_removes_archi_name_and_politeness():
    assert router.normalize("ArCHi, please open terminal") == "open terminal"
    assert router.normalize("archie volume up") == "volume up"


def test_registry_loads():
    by_phrase, by_id = router.load_commands()
    assert by_phrase["open terminal"]["id"] == "open_terminal"
    assert "identity" in by_id


def test_argv_expansion_is_portable(monkeypatch):
    monkeypatch.setattr(router, "ARCHI_BIN_DIR", Path("/tmp/archi-bin"))
    assert router.expand_argv(["{home}/Downloads", "{archi_bin}/archi-stop-speaking"]) == [
        f"{Path.home()}/Downloads",
        "/tmp/archi-bin/archi-stop-speaking",
    ]
