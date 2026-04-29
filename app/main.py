import logging

from contextlib import asynccontextmanager
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from zoneinfo import ZoneInfo

from app.exceptions.exceptions import register_all_errors
from app.jobs.currency_rates_job import update_currency_rates

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
from starlette.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

logging.getLogger("app").setLevel(logging.DEBUG)


load_dotenv(find_dotenv())

scheduler = AsyncIOScheduler(timezone=ZoneInfo("UTC"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        update_currency_rates,
        trigger="cron",
        hour=0,
        minute=30,
        id="update_currency_rates",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    scheduler.start()

    try:
        yield
    finally:
        scheduler.shutdown(wait=False)

app = FastAPI(title="Divvy API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_all_errors(app)

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
