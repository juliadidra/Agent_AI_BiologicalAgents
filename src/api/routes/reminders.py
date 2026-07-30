import logging

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from src.api.deps import get_reminder_service
from src.services.reminder_service import ReminderService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/agent/daily-reminders")
async def send_daily_reminders(
    service: ReminderService = Depends(get_reminder_service),
):
    sent = await run_in_threadpool(service.run_for_today)
    return JSONResponse(status_code=200, content={"sent": sent})
