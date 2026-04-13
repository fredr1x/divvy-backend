import json
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from ocr.services.const import SCHEMA, SYSTEM_PROMPT, AppState, lifespan
from ocr.services.filter_items import filter
from ocr.services.preprocess import preprocess_receipt

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

    results = await _process_multiple(files, state)

    receipt = filter(results)

    return receipt


async def _process_multiple(files: list[UploadFile], state: AppState):

    query_content = []

    logger.info()
    for f in files:
        img = await f.read()
        img_b64 = await preprocess_receipt(state, img)

        query_content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img_b64,
                },
            }
        )

    query_content.append(
        {"type": "text", "text": "Extract data as JSON from multiple receipts."}
    )

    raw = await state.vlm.messages.create(
        max_tokens=2048,
        model="claude-sonnet-4-6",
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": query_content,
            },
        ],
        output_config=SCHEMA,
    )

    parsed = json.loads(raw.content[0].text)

    return parsed
