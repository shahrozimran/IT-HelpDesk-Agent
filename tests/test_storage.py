import json
import subprocess
import sys
import pytest
from src.config import ROOT, local_path
from src.storage import Store


def test_preferences_survive_a_new_python_process_and_are_user_scoped(settings):
    store = Store(settings.data_dir)
    store.save_fact("alice", "session-a", "operating_system", "Windows 11")
    script = "import json,sys; from pathlib import Path; from src.storage import Store; print(json.dumps(Store(Path(sys.argv[1])).facts('alice')))"
    output = subprocess.check_output([sys.executable, "-c", script, str(settings.data_dir)], cwd=ROOT, text=True)
    assert json.loads(output) == {"operating_system": "Windows 11"}
    assert store.facts("bob") == {}


@pytest.mark.parametrize("key,value", [("password", "a-secret"), ("operating_system", "api_key=123"),
    ("response_style", ""), ("device_type", "x" * 161)])
def test_memory_rejects_unsupported_or_secret_values(settings, key, value):
    with pytest.raises(ValueError):
        Store(settings.data_dir).save_fact("alice", "s", key, value)


def test_confirmation_is_scoped_and_idempotent(settings):
    store = Store(settings.data_dir)
    draft = store.propose("alice", "s1", "Campus Wi-Fi unavailable", "wifi")
    assert "error" in store.create_ticket(draft["id"], "alice", "s1")
    with pytest.raises(ValueError):
        store.approve(draft["id"], "bob", "s1")
    with pytest.raises(ValueError):
        store.approve(draft["id"], "alice", "s2")
    store.approve(draft["id"], "alice", "s1")
    first = store.create_ticket(draft["id"], "alice", "s1")
    assert first["id"] == store.create_ticket(draft["id"], "alice", "s1")["id"]
    assert "error" in store.ticket(first["id"], "bob")
    assert store.ticket(first["id"], "alice")["status"] == "open"
    assert store.pending("alice", "s1") == []


def test_incidents_and_status_are_persistent_and_scoped(settings):
    store = Store(settings.data_dir)
    store.save_incident("alice", "Wi-Fi failed after basic checks; no credentials recorded.")
    assert len(Store(settings.data_dir).incidents("alice")) == 1
    assert store.incidents("bob") == []
    store.set_service("wifi", "outage", "Synthetic shared failure; recovery unknown")
    assert Store(settings.data_dir).service("wifi")["status"] == "outage"
    assert "error" in store.service("unknown")


def test_paths_cannot_escape_solution():
    with pytest.raises(ValueError):
        local_path(ROOT.parent / "outside-solution")
