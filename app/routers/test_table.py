from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import TestTable
from app.schemas.test_table import TestTableCreate, TestTableRead
from app.services.test_table_service import create_test_table
from app.services.test_table_service import get_all_from_test_table
from app.services.test_table_service import get_test_table_by_id

router = APIRouter(prefix="/test-tables", tags=["test-tables"])


@router.post("", response_model=TestTableRead)
def create_test_table_endpoint(
    payload: TestTableCreate,
    db: Session = Depends(get_db),
) -> TestTable:
    return create_test_table(db, payload)

@router.get("", response_model=list[TestTableRead])
def read_test_table_endpoint(
        db: Session = Depends(get_db)
) -> list[TestTable]:
    return get_all_from_test_table(db)

@router.get("/{id}", response_model=TestTableRead)
def read_test_table_endpoint(
    id: int,
    db: Session = Depends(get_db),
) -> TestTable:
    record = get_test_table_by_id(db, id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record
