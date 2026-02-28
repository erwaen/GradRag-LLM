from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OPENAI_API_KEY: str 
    CSRANKINGS_BASE_URL: str = "https://csrankings.org"
    GEMINI_API_KEY: str
    STORAGE_DIR: str = "data"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    COLLECTION_NAME: str = "advisors"
    COHERE_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    EMBEDDING_DIMENSIONS: int = 256
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"  # Ignora variables extra en el .env
    )

def get_settings():
    return Settings()
