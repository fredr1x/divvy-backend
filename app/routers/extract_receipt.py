from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_verified_user, get_ip_address
from app.models import User
from app.services.ocr.const import AppState, lifespan
from app.services.ocr.extract_service import extract_items


def get_models(request: Request) -> AppState:
    return request.app.state.models


router = APIRouter(lifespan=lifespan, tags=["ocr"])


@router.post("/scan-receipt")
async def scan_receipt(
    request: Request,
    group_id: int,
    expense_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    files: list[UploadFile] = File(...),
    state: AppState = Depends(get_models),
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

    result = await extract_items(
        ip_address=get_ip_address(request),
        group_id=group_id,
        expense_id=expense_id,
        db=db,
        current_user=current_user,
        files=files,
        state=state,
    )

    return result
