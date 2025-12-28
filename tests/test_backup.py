"""Backup utility tests."""

import sqlite3

from ipam import create_app
from ipam.backup import create_backup, list_backups, restore_backup


def _seed_db(path):
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS test_items (id INTEGER)")
        conn.execute("INSERT INTO test_items (id) VALUES (1)")
        conn.commit()
    finally:
        conn.close()


def _count_items(path):
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT COUNT(*) FROM test_items").fetchone()[0]
    finally:
        conn.close()


def test_backup_restore_cycle(tmp_path):
    db_path = tmp_path / "ipam.db"
    _seed_db(db_path)

    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["BACKUP_DIR"] = str(tmp_path / "backups")

    with app.app_context():
        backup_result = create_backup()
        backups = list_backups()

        assert backup_result["integrity_ok"] is True
        assert any(b.name == backup_result["name"] for b in backups)

        conn = sqlite3.connect(db_path)
        try:
            conn.execute("DELETE FROM test_items")
            conn.commit()
        finally:
            conn.close()

        assert _count_items(db_path) == 0

        restore_backup(backup_result["name"])

        assert _count_items(db_path) == 1
