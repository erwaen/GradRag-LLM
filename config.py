from pydantic import SecretStr
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OPENAI_API_KEY: str 
    CSRANKINGS_BASE_URL: str
    STORAGE_DIR: str
    QDRANT_URL: str
    QDRANT_API_KEY: str
    # COHERE_API_KEY: str
    STORAGE_DIR: str = "data"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8",)

def get_settings():
    return Settings()
