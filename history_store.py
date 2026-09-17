"""SQLite-backed download history (Phase 4).

Replaces the previous JSON list while keeping the same record fields. The
database lives next to the old ``download_history.json``; on first open the
JSON records are migrated once, then the JSON file is renamed to
``download_history.json.migrated`` as a backup.

All methods must be called from the main thread only (the GUI event pump owns
the connection).
"""

from __future__ import annotations

import json
import secrets
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

def _unique_record_id() -> str:
    """Timestamp id + random suffix: immune to Windows timer coalescing."""
    return datetime.now().strftime("%Y%m%d%H%M%S%f") + secrets.token_hex(2)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id TEXT PRIMARY KEY,
    time TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    output TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT '',
    details TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    chapters INTEGER NOT NULL DEFAULT 0,
    pages INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_history_created ON history(created_at);
CREATE TABLE IF NOT EXISTS history_events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    kind TEXT NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (record_id) REFERENCES history(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_history_events_record ON history_events(record_id);
"""

_SORT_COLUMNS = {"created_at", "source", "status", "details"}
_RECORD_KEYS = ("id", "time", "source", "output", "status", "details", "url", "chapters", "pages")


class HistoryStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        HistoryStore.self_check(db_path)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self._migrate_legacy_json()

    # ---------- phase 10.3: corruption recovery ----------

    @staticmethod
    def self_check(db_path: Path) -> None:
        """Validate the history database, recovering from a backup on damage.

        A readable file that is not a valid history database (or an unreadable
        one) is kept as <name>.corrupt and replaced by the newest <name>.bak.
        Called before the connection opens, so any exception here is fatal by
        design; callers may delete the file first to force a clean store.
        """
        if not db_path.exists() or db_path.stat().st_size == 0:
            return
        healthy = False
        try:
            conn = sqlite3.connect(str(db_path))
            try:
                integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
                tables = {row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                healthy = integrity == "ok" and {"history", "history_events"} <= tables
            finally:
                conn.close()
        except sqlite3.DatabaseError:
            healthy = False
        if healthy:
            return
        corrupt = db_path.with_suffix(db_path.suffix + ".corrupt")
        try:
            db_path.replace(corrupt)
        except OSError:
            return
        for backup in sorted(db_path.parent.glob(db_path.name + ".*.bak")):
            try:
                shutil.copy2(backup, db_path)
                break
            except OSError:
                continue

    def backup(self) -> None:
        """Snapshot the live database into timestamped <name>.<stamp>.bak.

        Keeps only the 3 newest backups; failures never break the caller.
        """
        stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        target = self.db_path.with_name(f"{self.db_path.name}.{stamp}.bak")
        try:
            self._conn.execute("VACUUM INTO ?", (str(target),))
            backups = sorted(self.db_path.parent.glob(self.db_path.name + ".*.bak"))
            for old in backups[:-3]:
                try:
                    old.unlink()
                except OSError:
                    pass
        except (sqlite3.Error, OSError):
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass

    # ---------- migration ----------

    def _migrate_legacy_json(self):
        legacy = self.db_path.parent / "download_history.json"
        try:
            records = json.loads(legacy.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(records, list) or not records:
            return
        existing = self._conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        if existing == 0:
            for index, record in enumerate(records):
                if not isinstance(record, dict):
                    continue
                record_id = str(record.get("id") or f"legacy-{index}")
                record_url = str(record.get("url") or record.get("source", ""))
                self._conn.execute(
                    "INSERT OR IGNORE INTO history"
                    " (id, time, source, output, status, details, url, chapters, pages, created_at)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        record_id,
                        str(record.get("time", "")),
                        str(record.get("source", "")),
                        str(record.get("output", "")),
                        str(record.get("status", "")),
                        str(record.get("details", "")),
                        record_url,
                        int(record.get("chapters", 0) or 0),
                        int(record.get("pages", 0) or 0),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                    ),
                )
            self._conn.commit()
        try:
            legacy.rename(legacy.with_suffix(".json.migrated"))
        except OSError:
            pass

    # ---------- writes ----------

    def add_record(self, record: dict) -> str:
        """Insert or replace a record; returns the record id used."""
        record_id = str(record.get("id") or _unique_record_id())
        self._conn.execute(
            "INSERT OR REPLACE INTO history"
            " (id, time, source, output, status, details, url, chapters, pages, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                record_id,
                str(record.get("time", "")),
                str(record.get("source", "")),
                str(record.get("output", "")),
                str(record.get("status", "")),
                str(record.get("details", "")),
                str(record.get("url", record.get("source", ""))),
                int(record.get("chapters", 0) or 0),
                int(record.get("pages", 0) or 0),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            ),
        )
        self._conn.commit()
        return record_id

    def update_record(self, record_id: str, **fields):
        allowed = {"time", "source", "output", "status", "details", "url", "chapters", "pages"}
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return
        assignments = ", ".join(f"{key} = ?" for key in updates)
        self._conn.execute(
            f"UPDATE history SET {assignments} WHERE id = ?",
            (*updates.values(), record_id),
        )
        self._conn.commit()

    def delete_records(self, record_ids) -> int:
        ids = list(record_ids)
        if not ids:
            return 0
        placeholders = ",".join("?" * len(ids))
        cursor = self._conn.execute(f"DELETE FROM history WHERE id IN ({placeholders})", ids)
        self._conn.commit()
        return cursor.rowcount

    def add_event(self, record_id: str, kind: str, message: str = ""):
        self._conn.execute(
            "INSERT INTO history_events (record_id, ts, kind, message) VALUES (?,?,?,?)",
            (record_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), kind, message),
        )
        self._conn.commit()
        self.prune_events(record_id)

    def prune_events(self, record_id: str, limit: int = 300):
        self._conn.execute(
            "DELETE FROM history_events WHERE record_id = ? AND seq NOT IN"
            " (SELECT seq FROM history_events WHERE record_id = ? ORDER BY seq DESC LIMIT ?)",
            (record_id, record_id, limit),
        )
        self._conn.commit()

    def events(self, record_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT ts, kind, message FROM history_events WHERE record_id = ? ORDER BY seq",
            (record_id,),
        ).fetchall()
        return [{"ts": row[0], "kind": row[1], "message": row[2]} for row in rows]

    # ---------- reads ----------

    def search(self, query: str = "", status_values=None, order_by: str = "created_at", descending: bool = True) -> list[dict]:
        """Filtered + sorted history records, newest first by default."""
        if order_by not in _SORT_COLUMNS:
            order_by = "created_at"
        sql = "SELECT id, time, source, output, status, details, url, chapters, pages FROM history"
        clauses: list[str] = []
        params: list[object] = []
        if query:
            like = f"%{query.lower()}%"
            clauses.append("(LOWER(source) LIKE ? OR LOWER(output) LIKE ? OR LOWER(status) LIKE ? OR LOWER(details) LIKE ?)")
            params.extend([like, like, like, like])
        status_values = list(status_values or ())
        if status_values:
            placeholders = ",".join("?" * len(status_values))
            clauses.append(f"status IN ({placeholders})")
            params.extend(status_values)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        direction = "DESC" if descending else "ASC"
        # rowid breaks ties and keeps legacy migrated order stable.
        sql += f" ORDER BY {order_by} {direction}, rowid {direction}"
        rows = self._conn.execute(sql, params).fetchall()
        return [dict(zip(_RECORD_KEYS, row)) for row in rows]

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]

    def close(self):
        try:
            self._conn.close()
        except sqlite3.Error:
            pass
