import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic
from fastapi import APIRouter

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    yolo: Any | None
    vlm: AsyncAnthropic
    detector_enabled: bool


def _model_path() -> str:
    return str((Path(__file__).resolve().parent / "detector.pt"))


async def _load_detector() -> Any | None:
    try:
        from ultralytics import YOLO

        return await asyncio.to_thread(YOLO, _model_path())
    except Exception as exc:
        logger.warning(
            "Local detector disabled, OCR will run without crop step: %s",
            exc,
        )
        return None


@asynccontextmanager
async def lifespan(router: APIRouter):

    yolo_model = await _load_detector()

    vlm_client = AsyncAnthropic(
        api_key=settings.CLAUDE_API_KEY,
        timeout=30.0,
        max_retries=2,
    )

    router.state.models = AppState(
        yolo=yolo_model,
        vlm=vlm_client,
        detector_enabled=yolo_model is not None,
    )

    logger.info("Loaded OCR clients. detector_enabled=%s", yolo_model is not None)

    yield

    await vlm_client.close()


def filter(receipt: list):

    to_remove_price_none = []
    for i, item in enumerate(receipt["items"]):
        if item["price"] is None:
            to_remove_price_none.append(i)

    for i in sorted(to_remove_price_none, reverse=True):
        receipt["items"].pop(i)

    return receipt
