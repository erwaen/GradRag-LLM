from pydantic import SecretStr
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    #AZURE_OPENAI_API_KEY: str
    OPENAI_API_KEY: str 
    #AZURE_OPENAI_ENDPOINT: str
    CSRANKINGS_BASE_URL: str
    STORAGE_DIR: str
    #SPIDER_API_KEY: str
    QDRANT_URL: str
    QDRANT_API_KEY: str
    COHERE_API_KEY: str
    #BING_API_KEY: str
    #BING_API_ENDPOINT: str
    #TAVILY_API_KEY: str
    STORAGE_DIR: str = "data"
    model_config = SettingsConfigDict(env_file=".env2", env_file_encoding="utf-8",)

def get_settings():
    return Settings()