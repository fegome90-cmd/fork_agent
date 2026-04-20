"""Rutas para webhooks.

NOTE: Webhooks are stored in-memory and are lost on API restart.
For persistent webhooks, use an external webhook management service.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from src.interfaces.api.dependencies import verify_api_key
from src.interfaces.api.models import (
    Webhook,
    WebhookCreate,
    WebhookListResponse,
    WebhookResponse,
    WebhookSafe,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_webhooks: dict[str, Webhook] = {}


def _to_safe_webhook(webhook: Webhook) -> WebhookSafe:
    return WebhookSafe(
        id=webhook.id,
        url=webhook.url,
        events=webhook.events,
    )


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    request: WebhookCreate,
    _: str = Depends(verify_api_key),
) -> WebhookResponse:
    logger.info(f"Creating webhook: url={request.url}")
    webhook_id = f"wh-{uuid.uuid4().hex[:6]}"
    webhook = Webhook(
        id=webhook_id,
        url=request.url,
        events=request.events,
        secret=request.secret,
    )
    _webhooks[webhook_id] = webhook
    logger.info(f"Webhook created: id={webhook_id}")
    return WebhookResponse(data=_to_safe_webhook(webhook))


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(_: str = Depends(verify_api_key)) -> WebhookListResponse:
    logger.info("Listing webhooks")
    safe_webhooks = [_to_safe_webhook(w) for w in _webhooks.values()]
    return WebhookListResponse(data=safe_webhooks)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    _: str = Depends(verify_api_key),
) -> None:
    logger.info(f"Deleting webhook: id={webhook_id}")
    if webhook_id not in _webhooks:
        raise HTTPException(status_code=404, detail="Webhook not found")
    del _webhooks[webhook_id]
