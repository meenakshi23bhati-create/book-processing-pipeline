from pydantic import BaseModel
from typing import Optional

class BookCreate(BaseModel):
    title :str
    total_pages : Optional[int]= None

class BookResponse(BaseModel):
    id : int
    title : str
    total_pages : Optional[int]
    status : str
    json_path : Optional[str]

    class config:
        from_attributes = True