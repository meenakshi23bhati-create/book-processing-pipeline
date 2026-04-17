import json
import os
from datetime import datetime
from sqlalchemy import create_engine,text
from app.core.config import settings

def save_chunks_to_json(book_id:int) -> str:
    """"DB se chunk fetch kar ke JSON File me save karta hai.
        output: /app/output/book_id{id}_{timestamp}.Json
    """

    engine=create_engine(settings.SYNC_DATABASE_URL)

    with engine.connect() as conn:
            book= conn.execute(
                text("SELECT * FROM  books  WHERE id = :bid"),
                {"bid": book_id}
            ).mappings().first()
            chunks= conn.execute(
            text("SELECT * FROM chunks WHERE book_id= :bid ORDER BY chunk_index"),
            {"bid": book_id}
        ).mappings().all()
    
    output={
          "book_id":book_id,
          "book_title": book["title"] if book  else "Unknown",
          "exported_at":datetime.utcnow().isoformat(),
          "total_chunks":len(chunks),
          "chunks":[
                {
                    "chunk_index":  c["chunk_index"],
                    "start_page":   c["start_page"],
                    "end_page":     c["end_page"],
                    "row_text":     c["row_text"],
                    "summary":      c["summary"],
                    "meta_data":    c["meta_data"],
                }
                for c in chunks
            ]
        }
    #output folder
    os.makedirs(settings.OUTPUT_DIR,exist_ok=True)

    #file save 
    timestamp= datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename=f"book_{book_id}_{timestamp}.json"
    filepath=os.path.join(settings.OUTPUT_DIR,filename)

    with open(filepath,"w",encoding="utf-8") as f:
          json.dump(output,f,ensure_ascii=False,indent=2)
    return filepath



