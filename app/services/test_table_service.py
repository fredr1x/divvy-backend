from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.test_table import TestTable
from app.schemas.test_table import TestTableCreate


def create_test_table(db: Session, data: TestTableCreate) -> TestTable:
    record = TestTable(text=data.text)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def get_all_from_test_table(db: Session) -> list[TestTable]:
    statement = select(TestTable)
    return list(db.scalars(statement))

def get_test_table_by_id(db: Session, id: int) -> TestTable | None:
    statement = select(TestTable).where(TestTable.id == id)
    return db.scalar(statement)
