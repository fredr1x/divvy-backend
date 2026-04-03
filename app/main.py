from fastapi import FastAPI

from app.routers import auth_router
from app.routers import test_table_router
from app.routers import group_router
from app.routers import user_group_router
from app.routers import group_expense_router
from app.routers import expense_split_router
from ocr.routers import ocr_router
from app.routers import group_media_router
from app.routers import minio_router

from dotenv import load_dotenv, find_dotenv
import logging

logging.basicConfig(
    level=logging.WARNING,  # default for everything
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

# Only elevate your own package
logging.getLogger("ocr").setLevel(logging.DEBUG)
logging.getLogger("app").setLevel(logging.DEBUG)


load_dotenv(find_dotenv())
app = FastAPI(title="Divvy API")

app.include_router(auth_router)

app.include_router(test_table_router)

app.include_router(group_router)

app.include_router(user_group_router)

app.include_router(group_expense_router)

app.include_router(expense_split_router)

app.include_router(ocr_router)

app.include_router(group_media_router)

app.include_router(minio_router)

@app.get("/")
def health_check():
    return {"status": "ok"}
