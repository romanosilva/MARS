import hashlib
import hmac
import json

from mars.db import Store
from mars.ingest import cloud_api
from mars.models import INBOUND, Message


def test_store_dedupes_messages():
    s = Store(":memory:")
    m = Message("id1", "jane", "Jane", INBOUND, 100, "text", "hi", "test")
    assert s.add_message(m) is True
    assert s.add_message(m) is False  # duplicate ignored
    assert len(s.messages_for_chat("jane")) == 1


def test_contact_upsert_tracks_span_and_name():
    s = Store(":memory:")
    s.upsert_contact("jane", "", 200)
    s.upsert_contact("jane", "Jane Doe", 100)
    c = s.find_contact("jane")
    assert c.display_name == "Jane Doe"
    assert c.first_seen_ts == 100 and c.last_seen_ts == 200


def test_find_contact_by_name_substring():
    s = Store(":memory:")
    s.upsert_contact("4915112345", "Professor Jane Doe", 1)
    assert s.find_contact("jane").wa_id == "4915112345"


def test_signature_verification():
    secret = "shh"
    body = b'{"hello":"world"}'
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert cloud_api.verify_signature(secret, body, sig) is True
    assert cloud_api.verify_signature(secret, body, "sha256=deadbeef") is False
    assert cloud_api.verify_signature(secret, body, "") is False


def test_subscription_handshake():
    assert cloud_api.verify_subscription("tok", "subscribe", "tok", "123") == "123"
    assert cloud_api.verify_subscription("tok", "subscribe", "bad", "123") is None


def test_parse_webhook_inbound_text():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "contacts": [{"wa_id": "4915112345",
                                  "profile": {"name": "Jane"}}],
                    "messages": [{
                        "from": "4915112345", "id": "wamid.X",
                        "timestamp": "1700000000", "type": "text",
                        "text": {"body": "hello professor"},
                    }],
                },
            }],
        }],
    }
    msgs = cloud_api.parse_webhook(payload)
    assert len(msgs) == 1
    assert msgs[0].direction == INBOUND
    assert msgs[0].sender_id == "Jane"
    assert msgs[0].body == "hello professor"
    assert cloud_api.contact_names(payload) == {"4915112345": "Jane"}
