import logging

from const import SYSTEM_PROMPT, AppState, ReceiptItem

logger = logging.getLogger(__name__)


async def call_qwen(state: AppState, img_b64: str):

    response = await state.qwen.chat.completions.create(
        model="qwen3-vl-flash",
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

    return response
