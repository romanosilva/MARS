"""FastAPI app exposing the Cloud API webhook endpoint.

Run with:  uvicorn mars.ingest.webhook:app --port 8080
Then point your Meta App's webhook callback URL at  https://<host>/webhook
using the same verify token as WHATSAPP_VERIFY_TOKEN.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, Response

from ..config import Config
from ..db import Store
from . import cloud_api

app = FastAPI(title="MARS WhatsApp ingest")
_config = Config.from_env()
_store = Store(_config.db_path)


@app.get("/webhook")
async def verify(request: Request) -> Response:
    q = request.query_params
    challenge = cloud_api.verify_subscription(
        _config.verify_token,
        q.get("hub.mode", ""),
        q.get("hub.verify_token", ""),
        q.get("hub.challenge", ""),
    )
    if challenge is None:
        return Response(status_code=403, content="verification failed")
    return Response(status_code=200, content=challenge)


@app.post("/webhook")
async def receive(request: Request) -> Response:
    raw = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    if _config.app_secret and not cloud_api.verify_signature(
        _config.app_secret, raw, sig
    ):
        return Response(status_code=403, content="bad signature")

    payload = await request.json()
    # Record/refresh contact names, then store any inbound messages.
    for wa_id, name in cloud_api.contact_names(payload).items():
        _store.upsert_contact(wa_id, name, 0)
    messages = cloud_api.parse_webhook(payload)
    for m in messages:
        _store.add_message(m)
        _store.upsert_contact(m.chat_id, m.sender_id, m.ts)
    _store.commit()

    # Always 200 quickly so Meta doesn't retry; processing is done above.
    return Response(status_code=200, content="ok")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "db": _config.db_path}
