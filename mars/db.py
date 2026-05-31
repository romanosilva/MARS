"""SQLite-backed local store. No data leaves this file unless you opt into
LLM summaries (which send only the messages for the contact you ask about)."""

from __future__ import annotations

import os
import sqlite3
from typing import Iterable, Optional

from .models import Contact, Message

_SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    wa_id          TEXT PRIMARY KEY,
    display_name   TEXT NOT NULL DEFAULT '',
    first_seen_ts  INTEGER NOT NULL,
    last_seen_ts   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    msg_id     TEXT PRIMARY KEY,
    chat_id    TEXT NOT NULL,
    sender_id  TEXT NOT NULL,
    direction  TEXT NOT NULL,
    ts         INTEGER NOT NULL,
    msg_type   TEXT NOT NULL,
    body       TEXT NOT NULL DEFAULT '',
    source     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_chat_ts ON messages (chat_id, ts);
CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages (ts);
"""


class Store:
    def __init__(self, db_path: str):
        self.db_path = db_path
        if db_path != ":memory:":
            parent = os.path.dirname(os.path.abspath(db_path))
            os.makedirs(parent, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # -- writes -----------------------------------------------------------
    def upsert_contact(self, wa_id: str, display_name: str, ts: int) -> None:
        self.conn.execute(
            """
            INSERT INTO contacts (wa_id, display_name, first_seen_ts, last_seen_ts)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(wa_id) DO UPDATE SET
                display_name = CASE
                    WHEN excluded.display_name != '' THEN excluded.display_name
                    ELSE contacts.display_name END,
                first_seen_ts = MIN(contacts.first_seen_ts, excluded.first_seen_ts),
                last_seen_ts  = MAX(contacts.last_seen_ts, excluded.last_seen_ts)
            """,
            (wa_id, display_name, ts, ts),
        )

    def add_message(self, m: Message) -> bool:
        """Insert a message. Returns True if newly inserted, False if duplicate."""
        cur = self.conn.execute(
            """
            INSERT OR IGNORE INTO messages
                (msg_id, chat_id, sender_id, direction, ts, msg_type, body, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (m.msg_id, m.chat_id, m.sender_id, m.direction, m.ts,
             m.msg_type, m.body, m.source),
        )
        return cur.rowcount > 0

    def add_messages(self, msgs: Iterable[Message]) -> int:
        n = sum(1 for m in msgs if self.add_message(m))
        self.conn.commit()
        return n

    def commit(self) -> None:
        self.conn.commit()

    # -- reads ------------------------------------------------------------
    def contacts(self) -> list[Contact]:
        rows = self.conn.execute(
            "SELECT * FROM contacts ORDER BY last_seen_ts DESC"
        ).fetchall()
        return [Contact(r["wa_id"], r["display_name"],
                        r["first_seen_ts"], r["last_seen_ts"]) for r in rows]

    def find_contact(self, needle: str) -> Optional[Contact]:
        """Match a contact by exact wa_id or case-insensitive name substring."""
        row = self.conn.execute(
            "SELECT * FROM contacts WHERE wa_id = ?", (needle,)
        ).fetchone()
        if row is None:
            row = self.conn.execute(
                "SELECT * FROM contacts WHERE display_name LIKE ? "
                "ORDER BY last_seen_ts DESC LIMIT 1",
                (f"%{needle}%",),
            ).fetchone()
        if row is None:
            return None
        return Contact(row["wa_id"], row["display_name"],
                       row["first_seen_ts"], row["last_seen_ts"])

    def messages_for_chat(self, chat_id: str) -> list[Message]:
        rows = self.conn.execute(
            "SELECT * FROM messages WHERE chat_id = ? ORDER BY ts ASC", (chat_id,)
        ).fetchall()
        return [self._row_to_message(r) for r in rows]

    def all_messages(self) -> list[Message]:
        rows = self.conn.execute(
            "SELECT * FROM messages ORDER BY ts ASC"
        ).fetchall()
        return [self._row_to_message(r) for r in rows]

    @staticmethod
    def _row_to_message(r: sqlite3.Row) -> Message:
        return Message(
            msg_id=r["msg_id"], chat_id=r["chat_id"], sender_id=r["sender_id"],
            direction=r["direction"], ts=r["ts"], msg_type=r["msg_type"],
            body=r["body"], source=r["source"],
        )

    def close(self) -> None:
        self.conn.close()
