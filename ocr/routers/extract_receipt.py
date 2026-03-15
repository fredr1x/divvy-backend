import asyncio
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from services.const import AppState, lifespan
from services.preprocess import preprocess_receipt
from services.qwen_client import call_qwen

logger = logging.getLogger(__name__)

def get_models(request: Request) -> AppState:
    return request.app.state.models


router = APIRouter(lifespan=lifespan)


@router.post("/scan-receipt")
async def scan_receipt(
    files: list[UploadFile] = File(...), state: AppState = Depends(get_models)
) -> dict:

    if not files:
        logger.warning("No Files Provided")
        raise HTTPException(422, "No files provided")

    results = await asyncio.gather(
        *[_process_single(f, state) for f in files],
        return_exceptions=True,
    )

    return {
        "results": [
            {"filename": files[i].filename, "result": r}
            if not isinstance(r, Exception)
            else {"filename": files[i].filename, "error": str(r)}
            for i, r in enumerate(results)
        ]
    }


async def _process_single(file: UploadFile, state: AppState) -> str:
    img_bytes = await file.read()

    img_b64 = preprocess_receipt(state, img_bytes)

    result = call_qwen(state, img_b64)

    return result
