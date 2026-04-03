import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field
from fastapi import APIRouter
from anthropic import AsyncAnthropic
import logging

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
        api_key=os.getenv("CLAUDE_API_KEY"),
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


class ReceiptItem(BaseModel):
    item_name: str = Field(description="Item name")
    price: float = Field(description="Price of the item", gt=0)
    quantity: int = Field(description="Total quanitity of the item", default=1)


SYSTEM_PROMPT = """
<system>
You are a receipt parsing engine. Extract structured data from receipt images and return valid JSON only. Do not include explanations, markdown, or any text outside the JSON object.

<task>
Parse every line-item from the receipt image and return a JSON array of purchased items.
</task>

<output_schema>
Return this exact structure:
{
  "items": [
    {
      "item_name": "<full product description as printed>",
      "quantity": <number>,
      "price": <number>
    }
  ]
}
</output_schema>

<field_rules>

  <item_name>
    - Copy the full description exactly as printed on the receipt
    - Include brand names, weights (e.g. "1КГ", "500гр"), barcodes, and product types
    - DO NOT truncate or summarize
    - DO NOT include price calculations in this field
  </item_name>

  <quantity>
    - Extract the quantity if explicitly shown
    - For weighted items (meat, produce, bulk goods), use 1 — do not extract the weight (e.g. 1.140 kg) as quantity
    - If no quantity is listed, default to 1
  </quantity>

  <price>
    - Extract the final line-item total only
    - If a calculation is shown (e.g. "1.140 × 2190.00 = 2496.60"), extract the result: 2496.60
    - Strip currency symbols — return a plain number
    - Never return a unit price when a line total is available
  </price>

</field_rules>

<scope>
  <include>Purchased goods list only</include>
  <exclude>
    - Store name, address, tax IDs, cashier info (header)
    - Subtotals, totals, taxes, discounts, payment method, QR codes (footer)
  </exclude>
</scope>

<language_note>
Receipt text may be in Kazakh, Russian, English, or a mix. Extract item names exactly as printed — do not translate.
</language_note>

<output_rules>
- Return only the JSON object
- No markdown fences (no ```json)
- No commentary before or after
- If the image contains no parseable items, return: {"items": []}
</output_rules>

</system>
"""
