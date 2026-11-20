"""SQLite storage: brand profile, connected accounts, media library, posts, insights, comments, activity log."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT NOT NULL, remote_id TEXT NOT NULL,
  username TEXT NOT NULL, name TEXT, picture TEXT, followers INTEGER DEFAULT 0,
  token TEXT, token_expires REAL, created REAL NOT NULL, UNIQUE(provider, remote_id));
CREATE TABLE IF NOT EXISTS media (
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, filename TEXT NOT NULL, mime TEXT NOT NULL,
  width INTEGER, height INTEGER, duration REAL, size INTEGER, title TEXT, notes TEXT,
  tags TEXT NOT NULL DEFAULT '[]', parent_id INTEGER, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, format TEXT NOT NULL,
  media_ids TEXT NOT NULL DEFAULT '[]', caption TEXT NOT NULL DEFAULT '', hashtags TEXT NOT NULL DEFAULT '[]',
  alt_text TEXT, first_comment TEXT, story_text TEXT, reel_hook TEXT, cover_ms INTEGER,
  lang TEXT NOT NULL DEFAULT 'tr', ai_label INTEGER NOT NULL DEFAULT 0, sponsored INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'draft', scheduled_at REAL, published_at REAL, remote_id TEXT, permalink TEXT,
  error TEXT, attempts INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL DEFAULT 'manual',
  rationale TEXT NOT NULL DEFAULT '[]', pillar TEXT, extra TEXT NOT NULL DEFAULT '{}', next_try REAL, created REAL NOT NULL, updated REAL NOT NULL);
CREATE INDEX IF NOT EXISTS posts_status ON posts(status, scheduled_at);
CREATE TABLE IF NOT EXISTS insights (
  post_id INTEGER PRIMARY KEY, ts REAL NOT NULL, reach INTEGER DEFAULT 0, views INTEGER DEFAULT 0,
  likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0, saves INTEGER DEFAULT 0, shares INTEGER DEFAULT 0,
  avg_watch_ms INTEGER DEFAULT 0, follows INTEGER DEFAULT 0, profile_visits INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, remote_id TEXT UNIQUE, username TEXT,
  text TEXT NOT NULL, ts REAL NOT NULL, intent TEXT, reply_draft TEXT, status TEXT NOT NULL DEFAULT 'open',
  reply_text TEXT);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, kind TEXT NOT NULL, message TEXT NOT NULL,
  post_id INTEGER);
"""

JSON_FIELDS = {"tags", "media_ids", "hashtags", "rationale", "extra"}
BOOL_FIELDS = {"ai_label", "sponsored"}


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    if r is None:
        return None
    d = dict(r)
    for k in JSON_FIELDS & d.keys():
        d[k] = json.loads(d[k] or ("{}" if k == "extra" else "[]"))
    for k in BOOL_FIELDS & d.keys():
        d[k] = bool(d[k])
    return d


def _enc(k: str, v: Any) -> Any:
    if k in JSON_FIELDS:
        return json.dumps(v if v is not None else ({} if k == "extra" else []), ensure_ascii=False)
    if k in BOOL_FIELDS:
        return int(bool(v))
    return v


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with self._con() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _con(self) -> Iterator[sqlite3.Connection]:
        """Commits and always closes, so no file handle stays open (matters on Windows)."""
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    # ---------- key/value (brand profile, preferences) ----------
    def get(self, key: str, default: Any = None) -> Any:
        with self._lock, self._con() as c:
            r = c.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return json.loads(r["value"]) if r else default

    def put(self, key: str, value: Any) -> None:
        with self._lock, self._con() as c:
            c.execute(
                "INSERT INTO kv(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value, ensure_ascii=False)),
            )

    # ---------- generic helpers ----------
    def _insert(self, table: str, data: dict[str, Any]) -> int:
        cols = list(data)
        with self._lock, self._con() as c:
            cur = c.execute(
                f"INSERT INTO {table}({','.join(cols)}) VALUES({','.join('?' * len(cols))})",
                [_enc(k, data[k]) for k in cols],
            )
            return int(cur.lastrowid or 0)

    def _update(self, table: str, row_id: int, data: dict[str, Any]) -> None:
        if not data:
            return
        with self._lock, self._con() as c:
            c.execute(
                f"UPDATE {table} SET {','.join(f'{k}=?' for k in data)} WHERE id=?",
                [*(_enc(k, v) for k, v in data.items()), row_id],
            )

    def _one(self, sql: str, args: tuple = ()) -> dict[str, Any] | None:
        with self._lock, self._con() as c:
            return _row(c.execute(sql, args).fetchone())

    def _all(self, sql: str, args: tuple = ()) -> list[dict[str, Any]]:
        with self._lock, self._con() as c:
            return [_row(r) for r in c.execute(sql, args).fetchall()]  # type: ignore[misc]

    # ---------- accounts ----------
    def upsert_account(self, provider: str, remote_id: str, **fields: Any) -> int:
        existing = self._one("SELECT id FROM accounts WHERE provider=? AND remote_id=?", (provider, remote_id))
        if existing:
            self._update("accounts", existing["id"], fields)
            return int(existing["id"])
        return self._insert(
            "accounts", {"provider": provider, "remote_id": remote_id, "created": time.time(), **fields}
        )

    def accounts(self) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM accounts ORDER BY id")

    def account(self, account_id: int) -> dict[str, Any] | None:
        return self._one("SELECT * FROM accounts WHERE id=?", (account_id,))

    def update_account(self, account_id: int, **fields: Any) -> None:
        self._update("accounts", account_id, fields)

    def delete_account(self, account_id: int) -> None:
        with self._lock, self._con() as c:
            c.execute("DELETE FROM accounts WHERE id=?", (account_id,))

    # ---------- media ----------
    def add_media(self, **fields: Any) -> int:
        return self._insert("media", {"created": time.time(), **fields})

    def media(self, media_id: int) -> dict[str, Any] | None:
        return self._one("SELECT * FROM media WHERE id=?", (media_id,))

    def media_list(self) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM media ORDER BY created DESC, id DESC")

    def update_media(self, media_id: int, **fields: Any) -> None:
        self._update("media", media_id, fields)

    def delete_media(self, media_id: int) -> None:
        with self._lock, self._con() as c:
            c.execute("DELETE FROM media WHERE id=?", (media_id,))

    def media_usage(self) -> dict[int, int]:
        """How many non-rejected posts use each media item."""
        counts: dict[int, int] = {}
        for p in self._all("SELECT media_ids FROM posts WHERE status != 'rejected'"):
            for m in p["media_ids"]:
                counts[m] = counts.get(m, 0) + 1
        return counts

    # ---------- posts ----------
    def add_post(self, **fields: Any) -> int:
        now = time.time()
        return self._insert("posts", {"created": now, "updated": now, **fields})

    def post(self, post_id: int) -> dict[str, Any] | None:
        return self._one(
            "SELECT p.*, i.reach, i.views, i.likes, i.comments AS comment_count, i.saves, i.shares, i.avg_watch_ms, "
            "i.follows, i.profile_visits FROM posts p LEFT JOIN insights i ON i.post_id = p.id WHERE p.id=?",
            (post_id,),
        )

    def posts(
        self, status: str | None = None, since: float | None = None, until: float | None = None
    ) -> list[dict[str, Any]]:
        sql = (
            "SELECT p.*, i.reach, i.views, i.likes, i.comments AS comment_count, i.saves, i.shares, i.avg_watch_ms, "
            "i.follows, i.profile_visits FROM posts p LEFT JOIN insights i ON i.post_id = p.id WHERE 1=1"
        )
        args: list[Any] = []
        if status:
            sql += f" AND p.status IN ({','.join('?' * len(status.split(',')))})"
            args += status.split(",")
        if since is not None:
            sql += " AND COALESCE(p.published_at, p.scheduled_at, p.created) >= ?"
            args.append(since)
        if until is not None:
            sql += " AND COALESCE(p.published_at, p.scheduled_at, p.created) < ?"
            args.append(until)
        sql += " ORDER BY COALESCE(p.scheduled_at, p.published_at, p.created), p.id"
        return self._all(sql, tuple(args))

    def update_post(self, post_id: int, **fields: Any) -> None:
        self._update("posts", post_id, {**fields, "updated": time.time()})

    def delete_post(self, post_id: int) -> None:
        with self._lock, self._con() as c:
            c.execute("DELETE FROM posts WHERE id=?", (post_id,))
            c.execute("DELETE FROM insights WHERE post_id=?", (post_id,))

    def due_posts(self, now: float) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM posts WHERE status IN ('approved','publishing') AND scheduled_at <= ? "
            "AND (next_try IS NULL OR next_try <= ?) ORDER BY scheduled_at",
            (now, now),
        )

    # ---------- insights ----------
    def save_insights(self, post_id: int, **m: int) -> None:
        cols = ["reach", "views", "likes", "comments", "saves", "shares", "avg_watch_ms", "follows", "profile_visits"]
        vals = [int(m.get(k, 0) or 0) for k in cols]
        with self._lock, self._con() as c:
            c.execute(
                f"INSERT INTO insights(post_id, ts, {','.join(cols)}) VALUES(?, ?, {','.join('?' * len(cols))}) "
                f"ON CONFLICT(post_id) DO UPDATE SET ts=excluded.ts, {','.join(f'{k}=excluded.{k}' for k in cols)}",
                [post_id, time.time(), *vals],
            )

    # ---------- comments ----------
    def add_comment(self, **fields: Any) -> int | None:
        if fields.get("remote_id") and self._one("SELECT id FROM comments WHERE remote_id=?", (fields["remote_id"],)):
            return None
        return self._insert("comments", fields)

    def comments(self, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            return self._all("SELECT * FROM comments WHERE status=? ORDER BY ts DESC", (status,))
        return self._all("SELECT * FROM comments ORDER BY ts DESC")

    def comment(self, comment_id: int) -> dict[str, Any] | None:
        return self._one("SELECT * FROM comments WHERE id=?", (comment_id,))

    def update_comment(self, comment_id: int, **fields: Any) -> None:
        self._update("comments", comment_id, fields)

    # ---------- activity log ----------
    def log(self, kind: str, message: str, post_id: int | None = None) -> None:
        self._insert("events", {"ts": time.time(), "kind": kind, "message": message, "post_id": post_id})

    def events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))
