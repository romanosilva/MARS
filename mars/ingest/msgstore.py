"""Import a *decrypted* WhatsApp msgstore.db (SQLite) into MARS.

This reads a local SQLite database you already obtained by decrypting your own
backup (e.g. with wa-crypt-tools on your device). MARS does not decrypt
backups and never touches your phone — it only reads a plain msgstore.db you
point it at.

WhatsApp has shipped two broad schema families; both are supported:

  legacy:  a single `messages` table keyed by `key_remote_jid`
  modern:  `message` rows joined through `chat` to a `jid` table

Timestamps in msgstore are milliseconds since epoch; we store seconds.
Contact *display names* live in a separate `wa.db`, not here, so contacts are
labelled by phone number (the jid user) unless a name is otherwise available.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ..models import INBOUND, OUTBOUND, Message

# WhatsApp media_wa_type / message_type integer -> our coarse type label.
_TYPE_MAP = {
    0: "text", 1: "image", 2: "audio", 3: "video", 4: "contact",
    5: "location", 7: "system", 9: "document", 13: "gif", 20: "sticker",
}

# jid servers we skip (not real conversations).
_SKIP_SERVERS = {"broadcast", "status"}


@dataclass
class ParsedStore:
    messages: list[Message]
    names: dict[str, str]  # chat_id -> best-known display label


def _connect_ro(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {r["name"] for r in rows}


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def _chat_id_and_kind(user: str, server: str, raw: str) -> tuple[str, bool]:
    """Return (chat_id, is_group). 1:1 chats key on the phone number to line
    up with Cloud API wa_ids; groups key on the full jid."""
    is_group = server == "g.us"
    return (raw if is_group else (user or raw)), is_group


def _coerce_ts(value) -> int:
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return 0
    return ts // 1000 if ts > 10_000_000_000 else ts  # ms -> s when needed


def _mk_message(key_id, from_me, ts, body, type_int, chat_id, sender_id):
    body = body or ""
    mtype = _TYPE_MAP.get(type_int, "text" if body else "media")
    direction = OUTBOUND if from_me else INBOUND
    mid = f"msgstore_{key_id}" if key_id else \
        f"msgstore_{chat_id}_{ts}_{1 if from_me else 0}_{hash(body) & 0xffffff:x}"
    return Message(msg_id=mid, chat_id=chat_id, sender_id=sender_id,
                   direction=direction, ts=ts, msg_type=mtype, body=body,
                   source="msgstore")


def _parse_modern(conn: sqlite3.Connection) -> ParsedStore:
    mcols = _columns(conn, "message")
    text_col = "text_data" if "text_data" in mcols else (
        "data" if "data" in mcols else None)
    type_col = "message_type" if "message_type" in mcols else None
    has_sender = "sender_jid_row_id" in mcols

    sql = f"""
        SELECT m.key_id            AS key_id,
               m.from_me           AS from_me,
               m.timestamp         AS ts,
               {('m.' + text_col) if text_col else 'NULL'}  AS body,
               {('m.' + type_col) if type_col else '0'}     AS type_int,
               cj.user AS c_user, cj.server AS c_server, cj.raw_string AS c_raw,
               {'sj.user' if has_sender else 'NULL'} AS s_user,
               {'sj.raw_string' if has_sender else 'NULL'} AS s_raw
        FROM message m
        JOIN chat c   ON m.chat_row_id = c._id
        JOIN jid  cj  ON c.jid_row_id  = cj._id
        {'LEFT JOIN jid sj ON m.sender_jid_row_id = sj._id' if has_sender else ''}
        WHERE m.timestamp IS NOT NULL
    """
    return _rows_to_store(conn.execute(sql).fetchall())


def _parse_legacy(conn: sqlite3.Connection) -> ParsedStore:
    cols = _columns(conn, "messages")
    text_col = "data" if "data" in cols else None
    type_col = "media_wa_type" if "media_wa_type" in cols else None
    sender_col = "remote_resource" if "remote_resource" in cols else None

    sql = f"""
        SELECT key_id                         AS key_id,
               key_from_me                    AS from_me,
               timestamp                      AS ts,
               {text_col or 'NULL'}           AS body,
               {type_col or '0'}              AS type_int,
               key_remote_jid                 AS c_raw,
               {sender_col or 'NULL'}         AS s_raw
        FROM messages
        WHERE timestamp IS NOT NULL AND key_remote_jid IS NOT NULL
    """
    rows = conn.execute(sql).fetchall()
    # Legacy stores the full jid string; split into user/server.
    norm = []
    for r in rows:
        raw = r["c_raw"] or ""
        user, _, server = raw.partition("@")
        norm.append({
            "key_id": r["key_id"], "from_me": r["from_me"], "ts": r["ts"],
            "body": r["body"], "type_int": r["type_int"],
            "c_user": user, "c_server": server, "c_raw": raw,
            "s_user": None, "s_raw": r["s_raw"],
        })
    return _rows_to_store(norm)


def _rows_to_store(rows) -> ParsedStore:
    messages: list[Message] = []
    names: dict[str, str] = {}
    for r in rows:
        server = (r["c_server"] or "")
        if server in _SKIP_SERVERS:
            continue
        chat_id, is_group = _chat_id_and_kind(
            r["c_user"] or "", server, r["c_raw"] or "")
        if not chat_id:
            continue
        ts = _coerce_ts(r["ts"])
        if ts == 0:
            continue
        # Sender label: groups use the per-message sender; 1:1 uses the chat.
        if is_group and not r["from_me"]:
            s_raw = r["s_raw"] or ""
            sender = (r["s_user"] or s_raw.partition("@")[0]) or chat_id
        else:
            sender = "me" if r["from_me"] else chat_id
        messages.append(_mk_message(
            r["key_id"], r["from_me"], ts, r["body"], r["type_int"],
            chat_id, sender))
        names.setdefault(chat_id, chat_id)
    return ParsedStore(messages=messages, names=names)


def parse_msgstore(path: str) -> ParsedStore:
    conn = _connect_ro(path)
    try:
        tables = _tables(conn)
        if {"message", "chat", "jid"} <= tables:
            return _parse_modern(conn)
        if "messages" in tables:
            return _parse_legacy(conn)
        raise ValueError(
            "Unrecognized msgstore schema: expected a 'message'+'chat'+'jid' "
            "(modern) or 'messages' (legacy) layout.")
    finally:
        conn.close()
