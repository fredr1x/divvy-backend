from pydantic import BaseModel, ConfigDict


class TestTableCreate(BaseModel):
    text: str


class TestTableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
