from pydantic import BaseModel, ConfigDict


class TestTableCreate(BaseModel):
    text: str


class TestTableRead(BaseModel):
    id: int
    text: str
    model_config = ConfigDict(from_attributes=True)
