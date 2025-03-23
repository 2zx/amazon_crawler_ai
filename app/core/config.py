import os
from typing import List, Optional, Any

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignora campi extra
    )

    # Informazioni sul progetto
    PROJECT_NAME: str = "Amazon Crawler"
    PROJECT_DESCRIPTION: str = "API per il crawling di prodotti Amazon"
    VERSION: str = "0.1.0"

    # Ambiente
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # API
    API_V1_STR: str = "/api/v1"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"

    # CORS
    CORS_ORIGINS: str = "*"

    # Database
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL", "sqlite:///./app.db"
    )

    # Alias per DATABASE_URL
    @property
    def DATABASE_URL(self) -> str:
        return self.SQLALCHEMY_DATABASE_URI

    # Crawling
    AMAZON_BASE_URL: str = "https://www.amazon.it"
    USER_AGENT_ROTATION: bool = True
    REQUEST_TIMEOUT: int = 10
    REQUEST_DELAY: float = 1.5  # Delay tra richieste in secondi
    MAX_RETRIES: int = 3

    # Proxy (opzionale)
    USE_PROXY: bool = False
    PROXY_URL: str = ""

    # Streamlit
    STREAMLIT_THEME: str = "light"
    STREAMLIT_SERVER_PORT: int = 8501
    STREAMLIT_TITLE: str = "Amazon Crawler Dashboard"

    # Google Cloud Run
    PORT: int = int(os.getenv("PORT", 8080))

    def get_cors_origins(self) -> List[str]:
        """
        Ottiene le origini CORS come lista, gestendo il caso speciale "*"
        """
        if self.CORS_ORIGINS == "*":
            return ["*"]

        if "," in self.CORS_ORIGINS:
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

        return [self.CORS_ORIGINS]


settings = Settings()
