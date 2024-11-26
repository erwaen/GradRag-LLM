from pydantic import SecretStr
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    AZURE_OPENAI_API_KEY: str 
    AZURE_OPENAI_ENDPOINT: str
    CSRANKINGS_BASE_URL: str
    STORAGE_DIR: str
    SPIDER_API_KEY: str
    qdrant_api_key: str

    model_config = SettingsConfigDict(env_file=".env")
    STORAGE_DIR: str = "data"
@lru_cache
def get_settings():
    return Settings()