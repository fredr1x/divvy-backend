import asyncio
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass

from anthropic import AsyncAnthropic
from fastapi import APIRouter
from pydantic import BaseModel, Field
from ultralytics import YOLO

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    yolo: YOLO
    vlm: AsyncAnthropic


@asynccontextmanager
async def lifespan(router: APIRouter):

    yolo_model = await asyncio.to_thread(YOLO, r"ocr\services\detector.pt")

    vlm_client = AsyncAnthropic(
        api_key=os.getenv("CLAUDE_API_KEY"),
        timeout=30.0,
        max_retries=2,
    )

    router.state.models = AppState(yolo=yolo_model, vlm=vlm_client)

    logger.info("Loaded YOLO and QWEN Client")

    yield

    await vlm_client.close()


class ReceiptItem(BaseModel):
    item_name: str = Field(description="Item name")
    price: float = Field(description="Price of the item", gt=0)
    quantity: int = Field(description="Total quanitity of the item", default=1)


SYSTEM_PROMPT = """
You are a receipt parsing engine. Extract every purchased line-item from the receipt image.

<field_rules>
  <item_name>
    Copy the full product description exactly as printed, including brand names,
    weights (e.g. "1КГ", "500гр"), and product types. Do not truncate or summarize.
  </item_name>

  <quantity>
    Use the explicitly printed quantity. For weighted items (meat, produce, bulk goods),
    use 1 — do not treat the weight (e.g. 1.140 kg) as quantity. Default to 1 if omitted.
  </quantity>

  <price>
    Extract the final line-item total. If a calculation is shown
    (e.g. "1.140 × 2190.00 = 2496.60"), extract only the result (2496.60).
    Strip currency symbols. Never return a unit price when a line total is available.
  </price>
</field_rules>

<scope>
  Extract purchased goods only.
  Ignore: store name, address, tax IDs, cashier info, subtotals, totals,
  taxes, discounts, payment method, QR codes.
</scope>

<language_note>
  Receipt text may be in Kazakh, Russian, English, or mixed.
  Extract item names exactly as printed — do not translate.
</language_note>
"""

SCHEMA = {
    "format": {
        "type": "json_schema",
        "name": "receipt_items",
        "schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_name": {
                                "type": "string",
                                "description": "Full product description exactly as printed on the receipt",
                            },
                            "quantity": {
                                "type": "integer",
                                "description": "Explicitly printed quantity, or 1 if not shown. Never use weight as quantity.",
                            },
                            "price": {
                                "type": ["number", "null"],
                                "description": "Final line-item total. Null if price is not visible or legible.",
                            },
                        },
                        "required": ["item_name", "quantity", "price"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["items"],
            "additionalProperties": False,
        },
    }
}
