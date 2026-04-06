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
    timezone: str = "America/New_York"
    screener_universes: str = "sp500,nasdaq100,tsx"
    watchlist_size: int = 20

    # Trading Mode
    trading_mode: str = "swing"  # "swing" or "day"

    # Exit Strategy Defaults (tuned for swing trading — daily ATR)
    default_stop_loss_pct: float = 5.0
    default_profit_target_pct: float = 10.0
    default_atr_multiplier_stop: float = 2.5
    default_atr_multiplier_target: float = 4.0
    eod_exit_enabled: bool = False
    max_hold_days: int = 25  # trading days (~5 weeks)

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
        return bool(self.massive_api_key)

    @property
    def has_anthropic_key(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()
