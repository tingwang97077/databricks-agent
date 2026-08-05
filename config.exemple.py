import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Lakebase Postgres connection
    # These will be auto-injected by Databricks Apps when Lakebase is configured as a resource
    db_host: str = os.environ.get("PGHOST", "your_instance")
    db_port: int = int(os.environ.get("PGPORT", "5432"))
    db_name: str = os.environ.get("PGDATABASE", "databricks_postgres")
    db_user: str = os.environ.get("PGUSER", "your_email")
    # Note: db_password is NOT needed - we use SDK token generation instead

    # App settings
    app_title: str = "your_app_name"
    page_icon: str = "🎫"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields like db_password from .env
    )


settings = Settings()
