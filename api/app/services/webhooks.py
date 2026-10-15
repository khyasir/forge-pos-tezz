import hashlib
import hmac
import json
import logging

import httpx
from sqlalchemy.orm import Session

from .. import models

logger = logging.getLogger("tezz.webhooks")


def sign_payload(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def send_event(db: Session, company_id: str, event: str, payload: dict) -> None:
    """Best-effort HMAC-signed webhook delivery. Errors are logged, never raised,
    so a slow/broken subscriber can't block the order flow.
    """
    hooks = (
        db.query(models.Webhook)
        .filter(models.Webhook.company_id == company_id, models.Webhook.active == True)  # noqa: E712
        .all()
    )
    for hook in hooks:
        if event not in [e.strip() for e in hook.events.split(",")]:
            continue
        body = json.dumps({"event": event, "data": payload}).encode()
        signature = sign_payload(hook.secret, body)
        try:
            httpx.post(
                hook.url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Tezz-Signature": signature,
                    "X-Tezz-Event": event,
                },
                timeout=5.0,
            )
        except httpx.HTTPError as exc:
            logger.warning("webhook delivery failed url=%s event=%s err=%s", hook.url, event, exc)
