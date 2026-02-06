from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.test_table import router as test_table_router

app = FastAPI(title="Divvy API")

app.include_router(auth_router)
app.include_router(test_table_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
