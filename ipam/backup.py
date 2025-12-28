"""Backup and restore utilities for SQLite."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List

from flask import current_app
from sqlalchemy.engine import make_url

from ipam.extensions import db


@dataclass(frozen=True)
class BackupInfo:
    """Metadata for a backup file."""

    name: str
    size_bytes: int
    created_at: str


def _get_db_path() -> str:
    """Return SQLite database path from app config."""
    url = make_url(current_app.config["SQLALCHEMY_DATABASE_URI"])
    if url.drivername != "sqlite":
        raise ValueError("Backups are only supported for SQLite databases.")
    if not url.database or url.database == ":memory:":
        raise ValueError("SQLite database path is not file-based.")
    return os.path.abspath(url.database)


def _get_backup_dir() -> str:
    """Ensure backup directory exists and return its path."""
    backup_dir = current_app.config["BACKUP_DIR"]
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def _backup_name() -> str:
    """Return a timestamped backup filename."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    return f"ipam-backup-{timestamp}.db"


def _resolve_backup_path(name: str) -> str:
    """Resolve and validate backup path."""
    backup_dir = _get_backup_dir()
    candidate = os.path.abspath(os.path.join(backup_dir, name))
    if os.path.commonpath([backup_dir, candidate]) != backup_dir:
        raise ValueError("Invalid backup name.")
    return candidate


def _integrity_check(path: str) -> Dict[str, str]:
    """Run SQLite integrity check on the given database file."""
    conn = sqlite3.connect(path)
    try:
        result = conn.execute("PRAGMA integrity_check;").fetchone()[0]
    finally:
        conn.close()
    return {"ok": result == "ok", "message": result}


def list_backups() -> List[BackupInfo]:
    """List available backups."""
    backup_dir = _get_backup_dir()
    backups = []
    for entry in sorted(os.listdir(backup_dir)):
        if not entry.endswith(".db"):
            continue
        path = os.path.join(backup_dir, entry)
        stat = os.stat(path)
        created_at = datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).isoformat()
        backups.append(
            BackupInfo(
                name=entry, size_bytes=stat.st_size, created_at=created_at
            )
        )
    return backups


def create_backup() -> Dict[str, object]:
    """Create a SQLite backup and return metadata."""
    db_path = _get_db_path()
    if not os.path.exists(db_path):
        raise ValueError("Database file not found.")

    backup_dir = _get_backup_dir()
    name = _backup_name()
    backup_path = os.path.join(backup_dir, name)

    source = sqlite3.connect(db_path)
    dest = sqlite3.connect(backup_path)
    try:
        source.backup(dest)
    finally:
        dest.close()
        source.close()

    integrity = _integrity_check(backup_path)
    stat = os.stat(backup_path)
    return {
        "name": name,
        "size_bytes": stat.st_size,
        "created_at": datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).isoformat(),
        "integrity_ok": integrity["ok"],
        "integrity_message": integrity["message"],
    }


def verify_backup(name: str) -> Dict[str, object]:
    """Verify integrity of a backup file."""
    backup_path = _resolve_backup_path(name)
    if not os.path.exists(backup_path):
        raise ValueError("Backup file not found.")
    integrity = _integrity_check(backup_path)
    return {
        "name": name,
        "integrity_ok": integrity["ok"],
        "integrity_message": integrity["message"],
    }


def restore_backup(name: str) -> Dict[str, object]:
    """Restore database from a backup file."""
    backup_path = _resolve_backup_path(name)
    if not os.path.exists(backup_path):
        raise ValueError("Backup file not found.")

    integrity = _integrity_check(backup_path)
    if not integrity["ok"]:
        raise ValueError("Backup integrity check failed.")

    db.engine.dispose()
    db_path = _get_db_path()
    source = sqlite3.connect(backup_path)
    dest = sqlite3.connect(db_path)
    try:
        source.backup(dest)
    finally:
        dest.close()
        source.close()

    return {
        "name": name,
        "restored": True,
        "integrity_ok": integrity["ok"],
        "integrity_message": integrity["message"],
    }
