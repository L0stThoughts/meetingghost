from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/db/meetingghost.db"
    OLLAMA_API_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "phi-3-mini"
    TRANSCRIBER_DEVICE: str = "cpu"
    SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"

    class Config:
        env_file = Path(".env")
        case_sensitive = False

settings = Settings()
