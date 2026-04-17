from pydantic import BaseModel
from typing import Optional, List

class ChunkResponse(BaseModel):
    id : int 
    book_id : int
    chunk_index :int 
    start_page : int
    end_page :int
    row_text :Optional[str]
    summary: Optional[str]
    meata_data : Optional[dict]

    class config:
        from_attributes = True

class ChunkListResponse(BaseModel):
    total_chunks= int
    chunks= List[ChunkResponse]