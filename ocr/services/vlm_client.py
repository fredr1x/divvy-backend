import logging
from time import time

from ocr.services.const import SYSTEM_PROMPT, AppState

logger = logging.getLogger(__name__)


async def call_vlm(state: AppState, img_b64: str):

    logger.info("Send receipt to the VLM")
    start = time()

    raw = await state.vlm.messages.create(
        max_tokens=1024,
        model="claude-sonnet-4-6",
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": img_b64,
                        },
                    },
                    {"type": "text", "text": "Extract receipt data as JSON."},
                ],
            },
        ],
    )

    logger.info(f"Get response from VLM in {time() - start} seconds")
    # logger.info(f"Token usage: {raw.usage}")
    if items := raw.content[0].text:
        # logger.info(items)
        return items

    raise Exception("Unable to analyze receipt", 500)
