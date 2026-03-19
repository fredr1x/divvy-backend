import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pydantic import BaseModel, Field
from fastapi import APIRouter
from openai import AsyncOpenAI
from ultralytics import YOLO
import logging

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    yolo: YOLO
    qwen: AsyncOpenAI


@asynccontextmanager
async def lifespan(router: APIRouter):

    yolo_model = await asyncio.to_thread(YOLO, r"ocr\services\detector.pt")

    qwen_client = AsyncOpenAI(
        base_url=os.getenv("QWEN_BASE_URL"),
        api_key=os.getenv("QWEN_API_KEY"),
        timeout=30.0,
        max_retries=2,
    )

    router.state.models = AppState(yolo=yolo_model, qwen=qwen_client)

    logger.info("Loaded YOLO and QWEN Client")

    yield

    await qwen_client.close()


class ReceiptItem(BaseModel):
    item_name: str = Field(description="Item name")
    price: float = Field(description="Price of the item", gt=0)
    quantity: int = Field(description="Total quanitity of the item", default=1)


SYSTEM_PROMPT = """
#Context#
You are a receipt parsing engine. Your only job is to extract structured data from receipt images and return it as valid JSON.

#Objective#
Accurately extract line-item information into a structured JSON format.
Identify every purchased item on the receipt and extract the following fields:
1.item_name: The full description of the product. This may include barcodes, brand names, weights (e.g., "1КГ", "500гр"), and product types. Do not truncate long names. Do not include price calculation.
2.quantity: The amount purchased.
For weighted items (e.g., meat, fruit), do not extract the specific weight (e.g., 1.140, 0.540).
Items where no quantity is listed, default the quantity to 1.
3.price: The total price charged for that specific line item (the final amount for that row). 
If a unit price and quantity are shown (e.g., "1.140 X 2190.00 = 2496.60"), extract the final total (2496.60).
Ignore currency symbols (like "Б" or "₸") in the numerical value, but note the currency if possible.

#Constraints & Guidelines#
Language: The receipt text may be in Kazakh, Russian, English or a mix. Extract the text exactly as it appears.
Filtering: Ignore header information (store name, address, tax IDs) and footer information (totals, payment methods, QR codes). Focus only on the list of purchased goods.
Accuracy: Ensure the price matches the line item total, not the unit price (unless they are the same).

Return JSON only. No assumptions. No inferred prices.

```json
{
  "items": [
    {
      "name": "string",
      "quantity": integer,
      "price": number | null
    }
  ]
}
"""
