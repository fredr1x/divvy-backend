import asyncio
import json
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from ocr.services.const import AppState, lifespan
from ocr.services.filter_items import filter
from ocr.services.preprocess import preprocess_receipt
from ocr.services.vlm_client import call_vlm

logger = logging.getLogger(__name__)


def get_models(request: Request) -> AppState:
    return request.app.state.models


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


router = APIRouter(lifespan=lifespan, tags=["ocr"])


@router.post("/scan-receipt")
async def scan_receipt(
    files: list[UploadFile] = File(...), state: AppState = Depends(get_models)
):

    if not files:
        logger.warning("No Files Provided")
        raise HTTPException(422, "No files provided")

    results = await asyncio.gather(
        *[_process_single(f, state) for f in files], return_exceptions=True
    )

    receipt = filter(results)

    return receipt


async def _process_single(file: UploadFile, state: AppState) -> str:
    img_bytes = await file.read()

    try:
        img_b64 = await preprocess_receipt(state, img_bytes)

        result = await call_vlm(state, img_b64)

        parsed = json.loads(_extract_json(result))

        return parsed
    except Exception as e:
        logger.error(e)
        return {"items": []}
