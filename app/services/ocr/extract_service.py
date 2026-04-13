import json
import logging

from fastapi import UploadFile

from app.schemas.item import ReceiptItems
from app.services.ocr.const import AppState, filter
from app.services.ocr.preprocess import preprocess_receipt
from app.services.ocr.prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def extract_items(files: list[UploadFile], state: AppState):

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

    logger.info("Sending files to Claude Sonnet")
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
        output_config={"format": ReceiptItems},
    )

    logger.info("Parsing result from Claude")

    parsed = json.loads(raw.content[0].text)

    return filter(parsed)
