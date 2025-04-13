# app/core/config.py
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from pathlib import Path

# Define the path to the .env file relative to this file
# This assumes config.py is in app/core/ and .env is in the project root
env_path = Path(__file__).resolve().parent.parent.parent / ".env" # Go up three levels from app/core/
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/sql_app.db")
    JINA_API_KEY: str = os.getenv("JINA_API_KEY")

    class Config:
        case_sensitive = True

settings = Settings()
