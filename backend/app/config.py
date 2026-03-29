from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

# .env lives at the project root (one level above backend/)
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://signal:signal@localhost:5555/signal_terminal"
    database_url_sync: str = "postgresql://signal:signal@localhost:5555/signal_terminal"
    redis_url: str = "redis://localhost:6380/0"

    # Market Data
    massive_api_key: str = ""
    finnhub_api_key: str = ""

    # AI
    anthropic_api_key: str = ""

    # Notifications
    resend_api_key: str = ""
    alert_email: str = ""

    # App
    use_simulated_data: bool = True
    timezone: str = "America/New_York"
    screener_universes: str = "sp500,nasdaq100,tsx"
    watchlist_size: int = 12

    # Exit Strategy Defaults
    default_stop_loss_pct: float = 2.0
    default_profit_target_pct: float = 3.0
    default_atr_multiplier_stop: float = 1.5
    default_atr_multiplier_target: float = 2.5
    eod_exit_warning_minutes: int = 15
    max_hold_bars: int = 60

    # Server
    cors_origins: list[str] = Field(default=["http://localhost:5173", "http://localhost:3000"])

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    @property
    def universes_list(self) -> list[str]:
        return [u.strip() for u in self.screener_universes.split(",")]

    @property
    def has_market_data_key(self) -> bool:
        return bool(self.massive_api_key or self.finnhub_api_key)

    @property
    def has_anthropic_key(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()
