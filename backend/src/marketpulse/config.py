from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

RunMode = Literal["LIVE_PAPER", "REPLAY", "TEST"]


class Settings(BaseSettings):
    app_name: str = "MarketPulse AI"
    run_mode: RunMode = "TEST"
    local_only: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = "postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5432/marketpulse"
    replay_database_url: str | None = None
    session_secret: SecretStr = SecretStr("dev-only-change-this-secret")
    admin_username: str = "admin"
    admin_password: SecretStr = SecretStr("dev-only-change-this-password")
    okx_rest_url: str = "https://www.okx.com"
    okx_ws_url: str = "wss://ws.okx.com:8443/ws/v5/public"
    ai_provider: str = "openai"
    ai_model: str = "gpt-5.6-terra"
    ai_timeout_seconds: float = 30.0
    ai_thinking: str = "high"
    ai_prompt_version: str = "g3-v1"
    ai_schema_version: str = "g3-v1"
    openai_api_key: SecretStr | None = None
    paper_initial_balance: float = 10_000.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def is_test(self) -> bool:
        return self.run_mode == "TEST"


@lru_cache
def get_settings() -> Settings:
    return Settings()
