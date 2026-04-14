import logging

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI

from app.routers import (
    auth_router,
    expense_split_router,
    group_expense_router,
    group_media_router,
    group_router,
    minio_router,
    scan_receipt,
    test_table_router,
    user_group_router,
    virtual_card_router,
)

logging.basicConfig(
    level=logging.WARNING,  # default for everything
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

# Only elevate your own package
logging.getLogger("app").setLevel(logging.DEBUG)


load_dotenv(find_dotenv())
app = FastAPI(title="Divvy API")

app.include_router(auth_router)

app.include_router(test_table_router)

app.include_router(group_router)

app.include_router(user_group_router)

app.include_router(group_expense_router)

app.include_router(expense_split_router)

app.include_router(scan_receipt)

app.include_router(group_media_router)

app.include_router(minio_router)

app.include_router(virtual_card_router)


@app.get("/")
def health_check():
    return {"status": "ok"}
