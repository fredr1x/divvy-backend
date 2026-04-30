import asyncio
import json

from anthropic import APIError
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AuditLog, User
from app.models.enums import ActionStatus, ActionType
from app.schemas.item import ReceiptItems, OutputSchema
from app.services.audit.audit_logs_service import create_failed_audit_log, create_log
from app.services.group.group_media_service import upload_receipt
from app.services.ocr.const import AppState
from app.services.ocr.preprocess import clean_and_merge, preprocess_receipt
from app.services.ocr.prompt import SYSTEM_PROMPT


async def extract_items(
    ip_address: str,
    group_id: int,
    expense_id: int | None,
    db: AsyncSession,
    current_user: User,
    files: list[UploadFile],
    state: AppState,
):
    audit_log: AuditLog = AuditLog(
        user_id=current_user.id,
        action_type=ActionType.EXTRACT,
        action_status=ActionStatus.SUCCESS,
        ip_address=ip_address,
        entity_name="EXTRACT_RECEIPT",
    )

    if not files:
        message = "No Files Provided"
        await create_failed_audit_log(db=db, audit_log=audit_log, message=message)
        raise HTTPException(422, "No files provided")

    if len(files) > 20:
        message = "Too much images in one request (Claude's maximum is 20 per request)"
        await create_failed_audit_log(db=db, audit_log=audit_log, message=message)
        raise HTTPException(400, "Number of images per request exceeded 20")

    _ = await upload_receipt(
        ip_address=ip_address,
        group_id=group_id,
        expense_id=expense_id,
        db=db,
        current_user=current_user,
        files=files,
    )

    audit_log.action_status=ActionStatus.SUCCESS
    await create_log(
        db=db, audit_log=audit_log, message="Sending files to Claude Sonnet"
    )

    raw_results = await asyncio.gather(
        *[_process_single(f, state) for f in files], return_exceptions=True
    )

    receipts: list[dict] = []
    failure_messages: list[str] = []
    for i, result in enumerate(raw_results):
        if isinstance(result, APIError):
            err_msg = f"Claude error for {files[i].filename}: {result}"
            failure_messages.append(err_msg)
            await create_failed_audit_log(
                db=db,
                audit_log=audit_log,
                message=err_msg,
            )
        elif isinstance(result, Exception):
            err_msg = f"Failed to extract {files[i].filename}: {type(result).__name__}: {result}"
            failure_messages.append(err_msg)
            await create_failed_audit_log(db=db, audit_log=audit_log, message=err_msg)
        elif result is None:
            err_msg = f"Extraction returned None for file {files[i].filename}"
            failure_messages.append(err_msg)
            await create_failed_audit_log(
                db=db,
                audit_log=audit_log,
                message=err_msg,
            )
        else:
            receipts.append(result)

    if not receipts:
        await create_failed_audit_log(
            db=db, audit_log=audit_log, message="No valid extraction results"
        )
        detail = "Could not extract receipt items from provided files"
        if failure_messages:
            detail = f"{detail}. Reasons: {' | '.join(failure_messages[:3])}"
        raise HTTPException(422, detail)

    merged_receipts = clean_and_merge(receipts)

    audit_log.action_status=ActionStatus.SUCCESS
    await create_log(
        db=db, audit_log=audit_log, message="Successfully Extracted Receipt items!"
    )

    return merged_receipts


async def call_vlm(img_b64: str, state: AppState):
    query_content = []

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

    raw = await state.vlm.messages.create(
        max_tokens=settings.CLAUDE_MAX_TOKENS,
        model=settings.CLAUDE_MODEL_ID,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": query_content,
            },
        ],
        output_config=OutputSchema
    )

    return json.loads(raw.content[0].text)


async def _process_single(file: UploadFile, state: AppState) -> dict:
    img_b64: str = await preprocess_receipt(file)  # ← await every async call
    response = await call_vlm(img_b64, state)  # ← await every async call
    return json.loads(response)
