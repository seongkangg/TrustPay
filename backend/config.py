"""Application settings, loaded once from the environment / .env.

See .env.example for every variable and its meaning.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    dev_log_file: str = "./logs/dev.log"  # full error detail; users only see a ref
    database_url: str = "sqlite:///./trustpay.db"
    cors_origins: str = "http://localhost:5173"

    llm_mode: str = "mock"  # "mock" | "watsonx" | "ollama"
    watsonx_api_key: str = ""
    watsonx_project_id: str = ""
    watsonx_url: str = "https://us-south.ml.cloud.ibm.com"
    watsonx_model_id: str = "ibm/granite-3-8b-instruct"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "granite3.3:8b"

    # Comma-separated mock names forced into failure mode: vendor, purchase_order, approval_limit, payment
    mock_failures: str = ""

    # Gmail intake (read-only). Off by default; needs the one-time `python -m backend.inbox.authorize`.
    inbox_enabled: bool = False
    inbox_poll_seconds: int = 10
    inbox_lookback_days: int = 30
    gmail_credentials_file: str = "./secrets/credentials.json"
    gmail_token_file: str = "./secrets/token.json"

    @property
    def failing_mocks(self) -> set[str]:
        return {m.strip() for m in self.mock_failures.split(",") if m.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
