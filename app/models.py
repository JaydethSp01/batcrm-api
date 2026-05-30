from pydantic import BaseModel

class Item(BaseModel):
    id: int | None = None
    name: str
