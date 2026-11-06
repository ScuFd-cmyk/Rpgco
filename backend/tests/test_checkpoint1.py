"""Checkpoint 1 acceptance tests (A-F from the master blueprint) plus
ownership/authorization rules."""
from __future__ import annotations

import threading

from backend.app.core.errors import Conflict
from backend.app.database import backup
from backend.app.database.db import connect
from backend.app.services import world

from .conftest import Player


def fortify_to(player, char_id, target):
    while player.get("/api/world").json()["state"]["ashenhold_defense"]["value"] < target:
        r = player.post("/api/world/actions", json={"character_id": char_id, "action": "fortify"})
        assert r.status_code == 200, r.text


# ---- Test A: character separation ----------------------------------------
def test_a_character_separation(two_players):
    a, ca, b, cb = two_players
    before_b = b.get(f"/api/characters/{cb['id']}").json()
    r = a.post(f"/api/characters/{ca['id']}/travel", json={"location_id": "whispering_wilds"})
    assert r.status_code == 200 and r.json()["location_id"] == "whispering_wilds"
    a.post(f"/api/characters/{ca['id']}/gather")
    after_a = a.get(f"/api/characters/{ca['id']}").json()
    after_b = b.get(f"/api/characters/{cb['id']}").json()
    assert after_a["experience"] == 1 and after_a["version"] > ca["version"]
    assert after_b == before_b


# ---- Test B: inventory separation ----------------------------------------
def test_b_inventory_separation(two_players):
    a, ca, b, cb = two_players
    a.post(f"/api/characters/{ca['id']}/travel", json={"location_id": "whispering_wilds"})
    r = a.post(f"/api/characters/{ca['id']}/gather")
    assert r.status_code == 200 and r.json()["item_id"] == "whisperleaf"
    a.post(f"/api/characters/{ca['id']}/gather")
    assert a.get(f"/api/characters/{ca['id']}/inventory").json() == [
        {"item_id": "whisperleaf", "name": "Whisperleaf", "quantity": 2}]
    assert b.get(f"/api/characters/{cb['id']}/inventory").json() == []


# ---- Test C: shared world --------------------------------------------------
def test_c_shared_world_visible_to_both(two_players):
    a, ca, b, cb = two_players
    assert b.get("/api/world").json()["state"]["ashenhold_defense"]["value"] == 0
    r = a.post("/api/world/actions", json={"character_id": ca["id"], "action": "fortify"})
    assert r.status_code == 200 and r.json()["value"] == 5
    seen_by_b = b.get("/api/world").json()
    assert seen_by_b["state"]["ashenhold_defense"]["value"] == 5
    assert {x["name"] for x in seen_by_b["adventurers"]} == {"Aldric", "Brisa"}
    assert "Aldric reinforced" in b.get("/api/chronicle").json()[0]["description"]


def test_world_state_gates_locations(two_players):
    a, ca, b, cb = two_players
    r = b.post(f"/api/characters/{cb['id']}/travel", json={"location_id": "hollow_bastion"})
    assert r.status_code == 400
    fortify_to(a, ca["id"], 50)  # Aldric's work opens the way for Brisa
    r = b.post(f"/api/characters/{cb['id']}/travel", json={"location_id": "hollow_bastion"})
    assert r.status_code == 200


# ---- Test D: persistence across restarts ----------------------------------
def test_d_persistence_across_restart(make_client):
    c1 = make_client()
    a, b = Player(c1, "alice"), Player(c1, "bram")
    ca = a.create_character("Aldric", "sentinel")
    cb = b.create_character("Brisa", "ranger")
    a.post(f"/api/characters/{ca['id']}/travel", json={"location_id": "whispering_wilds"})
    a.post(f"/api/characters/{ca['id']}/gather")
    b.post("/api/world/actions", json={"character_id": cb["id"], "action": "fortify"})
    c1.__exit__(None, None, None)  # server shuts down

    c2 = make_client()  # brand-new app instance, same data dir
    a.client = b.client = c2  # same browsers, existing session tokens
    char_a = a.get(f"/api/characters/{ca['id']}").json()
    assert char_a["location_id"] == "whispering_wilds" and char_a["experience"] == 1
    assert a.get(f"/api/characters/{ca['id']}/inventory").json()[0]["quantity"] == 1
    assert b.get(f"/api/characters/{cb['id']}").json()["class_id"] == "ranger"
    assert b.get("/api/world").json()["state"]["ashenhold_defense"]["value"] == 5
    # Login with passphrase also survives restart.
    assert c2.post("/api/sessions", json={"username": "alice", "passphrase": "secret-pass"}).status_code == 200


# ---- Test E: backup & recovery ---------------------------------------------
def test_e_backup_and_restore(make_client, settings):
    c1 = make_client()
    a, b = Player(c1, "alice"), Player(c1, "bram")
    ca = a.create_character("Aldric", "sentinel")
    cb = b.create_character("Brisa", "arcanist")
    a.post("/api/world/actions", json={"character_id": ca["id"], "action": "fortify"})
    snapshot = backup.create_backup(settings.db_path, settings.backup_dir, "test")
    assert backup.check_file(snapshot)

    # Damage the live data: delete a character, change the world.
    conn = connect(settings.db_path)
    conn.execute("DELETE FROM characters WHERE id = ?", (cb["id"],))
    conn.execute("UPDATE world_state SET value = '95' WHERE key = 'ashenhold_defense'")
    conn.close()
    assert b.get("/api/characters").json() == []
    c1.__exit__(None, None, None)  # restores are done with the server stopped

    safety = backup.restore_backup(snapshot, settings.db_path, settings.backup_dir)
    assert safety is not None and safety.exists()  # the damaged state is preserved too

    c2 = make_client()
    a.client = b.client = c2
    assert [c["name"] for c in b.get("/api/characters").json()] == ["Brisa"]
    assert [c["name"] for c in a.get("/api/characters").json()] == ["Aldric"]
    assert a.get("/api/world").json()["state"]["ashenhold_defense"]["value"] == 5


def test_backup_retention_keeps_pre_restore(settings, client):
    for _ in range(8):
        backup.create_backup(settings.db_path, settings.backup_dir, "auto", retain=settings.backup_retention)
    backup.create_backup(settings.db_path, settings.backup_dir, "pre-restore", retain=None)
    backup.prune(settings.backup_dir, settings.backup_retention)
    names = [p.name for p in backup.list_backups(settings.backup_dir)]
    assert len([n for n in names if "pre-restore" not in n]) == settings.backup_retention
    assert any("pre-restore" in n for n in names)


def test_restore_rejects_corrupt_backup(settings, client, tmp_path):
    bad = tmp_path / "world-bad.sqlite3"
    bad.write_bytes(b"not a database" * 100)
    try:
        backup.restore_backup(bad, settings.db_path, settings.backup_dir)
        raise AssertionError("expected failure")
    except RuntimeError:
        pass


# ---- Test F: concurrent updates --------------------------------------------
def test_f_concurrent_fortify_no_lost_updates(two_players, settings):
    """Two clients hammer the same world value simultaneously, each on its own
    DB connection and thread; every contribution must be counted."""
    a, ca, b, cb = two_players
    per_player = 8  # 2 * 8 * 5 = 80 <= DEFENSE_MAX
    errors = []
    barrier = threading.Barrier(2)

    def worker(char_id, account_id):
        conn = connect(settings.db_path)
        try:
            barrier.wait()
            for _ in range(per_player):
                world.fortify(conn, char_id, account_id)
        except Exception as e:  # pragma: no cover - surfaced below
            errors.append(e)
        finally:
            conn.close()

    acct = {r["id"]: r["account_id"] for r in connect(settings.db_path).execute("SELECT id, account_id FROM characters")}
    threads = [threading.Thread(target=worker, args=(c["id"], acct[c["id"]])) for c in (ca, cb)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors, errors
    state = a.get("/api/world").json()["state"]["ashenhold_defense"]
    assert state["value"] == 2 * per_player * 5
    assert state["version"] == 1 + 2 * per_player
    fortifies = [e for e in a.get("/api/chronicle?limit=500").json() if e["event_type"] == "fortify"]
    assert len(fortifies) == 2 * per_player


def test_f_optimistic_concurrency_rejects_stale_write(two_players, settings):
    """Both clients load v1; A writes first; B's write based on stale v1 is
    rejected with 409 rather than silently overwriting A's change."""
    a, ca, b, cb = two_players
    v_a = a.get("/api/world").json()["state"]["ashenhold_defense"]["version"]
    v_b = b.get("/api/world").json()["state"]["ashenhold_defense"]["version"]
    assert v_a == v_b
    r = a.post("/api/world/actions", json={"character_id": ca["id"], "action": "fortify", "expected_version": v_a})
    assert r.status_code == 200
    r = b.post("/api/world/actions", json={"character_id": cb["id"], "action": "fortify", "expected_version": v_b})
    assert r.status_code == 409
    assert b.get("/api/world").json()["state"]["ashenhold_defense"]["value"] == 5


def test_f_threaded_optimistic_retry_counter(two_players, settings):
    """Generic versioned update under contention: read-version/write with
    retry-on-conflict. No increment may be lost."""
    n, threads = 15, 4

    def worker():
        conn = connect(settings.db_path)
        done = 0
        while done < n:
            row = conn.execute("SELECT value, version FROM world_state WHERE key='ashenhold_defense'").fetchone()
            try:
                world.update_value(conn, "ashenhold_defense", int(row["value"]) + 1,
                                   expected_version=row["version"], description="test increment")
                done += 1
            except Conflict:
                continue
        conn.close()

    ts = [threading.Thread(target=worker) for _ in range(threads)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    a = two_players[0]
    assert a.get("/api/world").json()["state"]["ashenhold_defense"]["value"] == n * threads


# ---- Ownership / authorization ---------------------------------------------
def test_cannot_control_another_players_character(two_players):
    a, ca, b, cb = two_players
    assert b.get(f"/api/characters/{ca['id']}").status_code == 403
    assert b.post(f"/api/characters/{ca['id']}/travel", json={"location_id": "whispering_wilds"}).status_code == 403
    assert b.post(f"/api/characters/{ca['id']}/select").status_code == 403
    assert b.get(f"/api/characters/{ca['id']}/inventory").status_code == 403
    assert b.post("/api/world/actions", json={"character_id": ca["id"], "action": "fortify"}).status_code == 403
    assert a.get(f"/api/characters/{ca['id']}").json()["location_id"] == "ashenhold"


def test_requires_valid_session(client):
    assert client.get("/api/world").status_code == 401
    assert client.get("/api/world", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.post("/api/sessions", json={"username": "ghost", "passphrase": "whatever1"}).status_code == 401


def test_select_and_validation(two_players):
    a, ca, b, cb = two_players
    a2 = a.create_character("Ashe", "ranger")  # one account may own several characters
    assert a.post(f"/api/characters/{a2['id']}/select").status_code == 200
    assert a.get("/api/me").json()["selected_character_id"] == a2["id"]
    assert [c["name"] for c in a.get("/api/characters").json()] == ["Aldric", "Ashe"]
    assert a.post("/api/characters", json={"name": "Aldric", "class_id": "ranger"}).status_code == 409
    assert a.post("/api/characters", json={"name": "X", "class_id": "ranger"}).status_code == 422
    assert a.post("/api/characters", json={"name": "Valid Name", "class_id": "bard"}).status_code == 422
    assert a.post(f"/api/characters/{ca['id']}/gather").status_code == 400  # nothing in Ashenhold
