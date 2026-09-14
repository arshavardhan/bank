"""Application configuration settings."""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AI Financial Statement Analysis Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # LLM Provider: "gemini", "openai", or "mock" (for offline/deterministic testing)
    LLM_PROVIDER: str = "gemini"
    
    # LLM API Keys & Models
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL_NAME: str = "gpt-4o-mini"
    
    # Database
    DATABASE_URL: str = "sqlite:///./financial_agent.db"
    
    # Qdrant Vector Store
    QDRANT_LOCATION: str = ":memory:"  # ':memory:' or 'http://localhost:6333'
    QDRANT_COLLECTION_NAME: str = "statement_documents"
    
    # Observability (Langfuse)
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    LANGFUSE_ENABLED: bool = False
    
    # Security & Uploads
    MAX_UPLOAD_SIZE_MB: int = 25
    ALLOWED_EXTENSIONS: List[str] = ["csv", "xlsx", "xls", "pdf", "png", "jpg", "jpeg"]
    
    # Storage
    UPLOAD_DIR: str = "./uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
