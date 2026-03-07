from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.test_table import router as test_table_router
from app.routers.group import router as group_router
from app.routers.user_group import router as user_group_router
from app.routers.group_expense import router as group_expense_router
from app.routers.expense_split import router as expense_split_router
app = FastAPI(title="Divvy API")

app.include_router(auth_router)

app.include_router(test_table_router)

app.include_router(group_router)

app.include_router(user_group_router)

app.include_router(group_expense_router)

app.include_router(expense_split_router)

@app.get("/")
def health_check():
    return {"status": "ok"}
