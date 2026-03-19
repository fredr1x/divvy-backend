import logging
from ocr.services.const import SYSTEM_PROMPT, AppState
from time import time
logger = logging.getLogger(__name__)


async def call_qwen(state: AppState, img_b64: str):

    logger.info("Send receipt to the QWEN")
    start = time()
    raw = await state.qwen.chat.completions.create(
        model="qwen3.5-flash",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                    },
                    {"type": "text", "text": "Extract receipt data as JSON."},
                ],
            },
        ],
        max_tokens=1024,
        response_format={"type": "json_object"},
        temperature=0,
    )

    logger.info(f"Get response from QWEN in {time() - start} seconds")

    if items := raw.choices[0].message.content:
        logger.info(items)
        return items
    
    raise Exception("Unable to analyze receipt", 500)
