import asyncio
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from ocr.services.const import AppState, lifespan
from ocr.services.preprocess import preprocess_receipt
from ocr.services.qwen_client import call_qwen
import json


logger = logging.getLogger(__name__)

def get_models(request: Request) -> AppState:
    return request.app.state.models


router = APIRouter(lifespan=lifespan, tags=["ocr"])


@router.post("/scan-receipt")
async def scan_receipt(
    files: list[UploadFile] = File(...), state: AppState = Depends(get_models)
):

    if not files:
        logger.warning("No Files Provided")
        raise HTTPException(422, "No files provided")

    results = await asyncio.gather(
        *[_process_single(f, state) for f in files],
        return_exceptions=True
    )

    receipt = results[0]
    if len(results) > 1:
        for r in results[1:]:
            receipt['items'].extend(r['items'])

    return receipt



async def _process_single(file: UploadFile, state: AppState) -> str:
    img_bytes = await file.read()

    try:
        img_b64 = await preprocess_receipt(state, img_bytes)

        result = await call_qwen(state, img_b64)
        
        parsed = json.loads(result)

        return parsed
    except Exception as e:
        logger.error(e)
        return {
            "items":[]
        }

