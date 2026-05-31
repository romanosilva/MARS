import sqlite3

import pytest

from mars.ingest.msgstore import parse_msgstore
from mars.models import INBOUND, OUTBOUND

TS_MS = 1_700_000_000_000          # milliseconds
TS_S = TS_MS // 1000               # expected stored seconds


def _modern_db(path):
    c = sqlite3.connect(path)
    c.executescript("""
        CREATE TABLE jid (_id INTEGER PRIMARY KEY, user TEXT, server TEXT,
                          raw_string TEXT);
        CREATE TABLE chat (_id INTEGER PRIMARY KEY, jid_row_id INTEGER);
        CREATE TABLE message (_id INTEGER PRIMARY KEY, chat_row_id INTEGER,
                              from_me INTEGER, key_id TEXT, timestamp INTEGER,
                              text_data TEXT, message_type INTEGER,
                              sender_jid_row_id INTEGER);
    """)
    # jids: a 1:1 contact, a group, and a group member.
    c.executemany("INSERT INTO jid VALUES (?,?,?,?)", [
        (1, "4915112345", "s.whatsapp.net", "4915112345@s.whatsapp.net"),
        (2, "120363000", "g.us", "120363000@g.us"),
        (3, "4915199999", "s.whatsapp.net", "4915199999@s.whatsapp.net"),
        (4, "status", "broadcast", "status@broadcast"),
    ])
    c.executemany("INSERT INTO chat VALUES (?,?)", [(1, 1), (2, 2), (3, 4)])
    c.executemany(
        "INSERT INTO message VALUES (?,?,?,?,?,?,?,?)",
        [
            (1, 1, 0, "k1", TS_MS, "hello professor", 0, None),       # inbound 1:1
            (2, 1, 1, "k2", TS_MS + 60000, "hi there", 0, None),      # outbound 1:1
            (3, 1, 0, "k3", TS_MS + 120000, None, 1, None),           # inbound image
            (4, 2, 0, "k4", TS_MS, "group msg", 0, 3),                # group, from member
            (5, 3, 0, "k5", TS_MS, "status update", 0, None),         # status -> skipped
        ],
    )
    c.commit()
    c.close()


def _legacy_db(path):
    c = sqlite3.connect(path)
    c.executescript("""
        CREATE TABLE messages (_id INTEGER PRIMARY KEY, key_remote_jid TEXT,
                               key_from_me INTEGER, key_id TEXT, timestamp INTEGER,
                               data TEXT, media_wa_type INTEGER,
                               remote_resource TEXT);
    """)
    c.executemany(
        "INSERT INTO messages VALUES (?,?,?,?,?,?,?,?)",
        [
            (1, "4915112345@s.whatsapp.net", 0, "k1", TS_MS, "hi prof", 0, None),
            (2, "4915112345@s.whatsapp.net", 1, "k2", TS_MS + 60000, "hello", 0, None),
            (3, "120363000@g.us", 0, "k3", TS_MS, "grp", 0,
             "4915199999@s.whatsapp.net"),
        ],
    )
    c.commit()
    c.close()


def test_modern_schema(tmp_path):
    db = str(tmp_path / "msgstore.db")
    _modern_db(db)
    parsed = parse_msgstore(db)

    # status@broadcast row dropped; 4 real messages remain.
    assert len(parsed.messages) == 4
    by_id = {m.msg_id: m for m in parsed.messages}

    one_to_one_in = by_id["msgstore_k1"]
    assert one_to_one_in.direction == INBOUND
    assert one_to_one_in.chat_id == "4915112345"   # keyed by phone, like Cloud API
    assert one_to_one_in.ts == TS_S                # ms converted to s
    assert one_to_one_in.body == "hello professor"

    assert by_id["msgstore_k2"].direction == OUTBOUND
    assert by_id["msgstore_k3"].msg_type == "image"

    grp = by_id["msgstore_k4"]
    assert grp.chat_id == "120363000@g.us"         # groups keyed by full jid
    assert grp.sender_id == "4915199999"           # resolved group member


def test_legacy_schema(tmp_path):
    db = str(tmp_path / "msgstore.db")
    _legacy_db(db)
    parsed = parse_msgstore(db)
    assert len(parsed.messages) == 3
    by_id = {m.msg_id: m for m in parsed.messages}
    assert by_id["msgstore_k1"].chat_id == "4915112345"
    assert by_id["msgstore_k2"].direction == OUTBOUND
    assert by_id["msgstore_k3"].chat_id == "120363000@g.us"
    assert by_id["msgstore_k3"].sender_id == "4915199999"


def test_unknown_schema_raises(tmp_path):
    db = str(tmp_path / "weird.db")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE nope (_id INTEGER)")
    c.commit()
    c.close()
    with pytest.raises(ValueError):
        parse_msgstore(db)
