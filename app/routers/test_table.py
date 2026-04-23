from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import TestTable
from app.schemas.test_table import TestTableCreate, TestTableRead
from app.services.test_table_service import create_test_table
from app.services.test_table_service import get_all_from_test_table
from app.services.test_table_service import get_test_table_by_id
from app.services.test_table_service import delete_test_by_id

router = APIRouter(prefix="/test-tables", tags=["test-tables"])


@router.post("", response_model=TestTableRead)
async def create_test_table_endpoint(
    payload: TestTableCreate,
    db: AsyncSession = Depends(get_db),
) -> TestTable:
    return await create_test_table(db, payload)

@router.get("", response_model=list[TestTableRead])
async def read_test_table_endpoint(
        db: AsyncSession = Depends(get_db)
) -> list[TestTable]:
    return await get_all_from_test_table(db)

@router.get("/{id}", response_model=TestTableRead)
async def read_test_table_endpoint(
    id: int,
    db: AsyncSession = Depends(get_db),
) -> TestTable:
    record = await get_test_table_by_id(db, id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record

@router.delete("/{id}", status_code=204)
async def delete_test_table_endpoint(
        id: int,
        db: AsyncSession = Depends(get_db)):
    await delete_test_by_id(db, id)
