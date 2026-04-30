import asyncio
import base64
from PIL import Image
import numpy as np
import io

from app.services.ocr.const import AppState


async def preprocess_receipt(state: AppState, img_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(img_bytes))
    if img is None:
        raise ValueError("Unable to decode uploaded image")
    
    if state.yolo is not None:
        img_array = np.array(img)
        results = await asyncio.to_thread(state.yolo.predict, img_array, verbose=False)
        img = _crop_receipt(img, results)

    buffer = io.BytesIO()
    # img.save(buffer, format="JPEG")
    b64 = base64.b64encode(buffer.getvalue()).decode()

    return b64


async def _crop_receipt(img: np.ndarray, results) -> np.ndarray:
    if not results or len(results[0].boxes) == 0:
        return img

    box = results[0].boxes.xyxy[0].cpu().numpy().astype(np.uint16)
    x1, y1, x2, y2 = box
    return img[y1:y2, x1:x2]


async def clean_and_merge(receipts: list[dict]):

    merged: dict = receipts[0]
    for r in receipts[1:]:
        merged["items"].extend(r.get("items", []))

    to_remove = [
        i for i in range(len(merged["items"])) if not merged["items"][i]["price"]
    ]

    for i in sorted(to_remove, reverse=True):
        merged["items"].pop(i)

    return merged
