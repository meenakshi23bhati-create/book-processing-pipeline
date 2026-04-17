from pydantic_settings import BaseSettings
from typing import ClassVar

class Settings(BaseSettings):
    
    DATABASE_URL:str ="postgresql+asyncpg://bookuser:bookpass@db:5432/bookdb"
    
    REDIS_URL:str = "redis://redis:6379/0"
    OPENAI_API_KEY:str = " "
    CHUNK_SIZE: int = 20
    OUTPUT_DIR:str ="/app/output"
    SYNC_DATABASE_URL: ClassVar[str] = "postgresql+psycopg2://bookuser:bookpass@db:5432/bookdb"
    class Config:
        env_file = ".env"

settings = Settings() 