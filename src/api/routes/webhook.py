import logging

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.api.deps import get_container
from src.api.dto import IncomingMessagePayload, WebhookEnvelope
from src.core.container import Container

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/agent/webhook")
async def agent_webhook(
    request: Request,
    container: Container = Depends(get_container),
):
    raw = await request.json()
    logger.info("Webhook received: %s", raw)

    envelope = WebhookEnvelope.model_validate(raw)
    if not envelope.payload:
        return JSONResponse(
            status_code=200,
            content={"ignored": "missing or invalid 'payload'"},
        )

    try:
        message = IncomingMessagePayload.model_validate(envelope.payload)
    except ValidationError:
        return JSONResponse(
            status_code=200,
            content={"ignored": "non-message event"},
        )

    if not message.body or not message.body.strip():
        return JSONResponse(
            status_code=200,
            content={"ignored": "non-message event"},
        )

    result = await run_in_threadpool(
        container.inbox_service.process_message,
        message.chat_id,
        message.body,
    )
    return JSONResponse(status_code=200, content=result)
