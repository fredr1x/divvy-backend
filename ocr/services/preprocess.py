import asyncio
import base64

import cv2
import numpy as np
from ocr.services.const import AppState



async def preprocess_receipt(state: AppState, img_bytes) -> str:

    img_array = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Unable to decode uploaded image")

    if state.yolo is not None:
        results = await asyncio.to_thread(state.yolo.predict, img, verbose=False)
        cropped = _crop_receipt(img, results)
    else:
        cropped = img

    b64 = base64.b64encode(cv2.imencode(".jpg", cropped)[1]).decode()

    return b64


def _crop_receipt(img: np.ndarray, results) -> np.ndarray:
    # If YOLO found nothing, return original — don't crash
    if not results or len(results[0].boxes) == 0:
        return img

    box = results[0].boxes.xyxy[0].cpu().numpy().astype(np.uint16)
    x1, y1, x2, y2 = box
    return img[y1:y2, x1:x2]
