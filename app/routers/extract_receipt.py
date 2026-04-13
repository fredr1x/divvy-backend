import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.services.ocr.const import AppState, lifespan
from app.services.ocr.extract_service import extract_items

logger = logging.getLogger(__name__)


def get_models(request: Request) -> AppState:
    return request.app.state.models


router = APIRouter(lifespan=lifespan, tags=["ocr"])


@router.post("/scan-receipt")
async def scan_receipt(
    files: list[UploadFile] = File(...), state: AppState = Depends(get_models)
):
    """
    Scan and extract receipt items using OCR and AI.

    Processes receipt images using YOLO object detection and Claude AI
    to extract purchased items, prices, and quantities.
    Supports batch processing of multiple receipt images.

    Args:
        files: List of receipt image files to process
        state: Application state containing YOLO and Claude models

    Returns:
        dict: Processed receipts with extracted items including:
            - item_name: Product description
            - price: Item price
            - quantity: Quantity purchased

    Raises:
        HTTPException 400: If file upload or processing fails
    """

    if not files:
        logger.warning("No Files Provided")
        raise HTTPException(422, "No files provided")

    if len(files) > 20:
        logger.error(
            "Too much images in one request (Claude's maximum is 20 per request)"
        )
        raise HTTPException(400, "Number of images per request exceeded 20")

    result = await extract_items(files, state)

    return result
