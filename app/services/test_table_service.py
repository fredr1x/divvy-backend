from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_table import TestTable
from app.schemas.test_table import TestTableCreate


async def create_test_table(db: AsyncSession, data: TestTableCreate) -> TestTable:
    record = TestTable(text=data.text)
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record

async def get_all_from_test_table(db: AsyncSession) -> list[TestTable]:
    statement = select(TestTable)
    return list((await db.scalars(statement)).all())

async def get_test_table_by_id(db: AsyncSession, id: int) -> TestTable | None:
    statement = select(TestTable).where(TestTable.id == id)
    return await db.scalar(statement)

async def delete_test_by_id(db: AsyncSession, id: int) -> None:
    test = await db.get(TestTable, id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    await db.delete(test)
