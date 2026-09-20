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

    # --- PRE-01B Integrated Runtime Host (Host Core V1) -------------------------------
    # Ownership, not activation: the RuntimeHost is never composed implicitly, and every
    # value below is an operational default rather than a correctness constant. In
    # particular `runtime_safety_queue_capacity` is the accepted *initial* default that
    # Implementation Acceptance must size with observed queue high-water evidence
    # (PRE-01B-D1 carry-in F-02); it is deliberately a bounded setting, never a literal
    # frozen into the Host.
    runtime_host_enabled: bool = False
    runtime_host_instruments: str = "BTC-USDT,ETH-USDT"
    runtime_workers: int = 1
    runtime_reload: bool = False
    runtime_startup_timeout_seconds: float = 60.0
    runtime_shutdown_grace_seconds: float = 30.0
    runtime_shutdown_dispose_seconds: float = 5.0
    runtime_safety_queue_capacity: int = 64
    runtime_scanner_queue_capacity: int = 2048
    runtime_market_freshness_seconds: float = 5.0
    runtime_heartbeat_interval_seconds: float = 5.0
    runtime_reconciliation_interval_seconds: float = 60.0
    runtime_telemetry_interval_seconds: float = 5.0
    runtime_database_application_name: str = "marketpulse-runtime-host"
    # Stable cross-process namespace for the duplicate-Host advisory lock. Only the
    # namespace + `run_mode` key are used; the lock needs no schema and no migration.
    runtime_advisory_lock_namespace: int = 0x4D50
    # PRE-01B-I2 is disabled by default. A Gate-A value is intentionally not a
    # switch: RuntimeHost rejects it until a separate activation batch supplies
    # the complete Pack-B configuration and authorizes composition.
    advisory_activation_level: str = "DISABLED"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def is_test(self) -> bool:
        return self.run_mode == "TEST"

    @property
    def runtime_host_instrument_list(self) -> list[str]:
        """Configured Host subscriptions in declaration order, de-duplicated."""
        seen: dict[str, None] = {}
        for item in self.runtime_host_instruments.split(","):
            symbol = item.strip().upper()
            if symbol:
                seen.setdefault(symbol, None)
        return list(seen)


@lru_cache
def get_settings() -> Settings:
    return Settings()
