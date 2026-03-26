from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from app.models.position import Position


class ExitUrgency(str, Enum):
    CRITICAL = "critical"   # Exit NOW — stop loss hit, circuit breaker
    HIGH = "high"           # Exit soon — target hit, strong reversal
    MEDIUM = "medium"       # Consider exiting — indicator weakening
    LOW = "low"             # Heads up — sentiment shifting, time warning


@dataclass
class ExitSignalResult:
    triggered: bool
    exit_type: str           # stop_loss, profit_target, indicator_reversal, etc.
    urgency: ExitUrgency
    trigger_price: float | None
    current_price: float
    message: str             # Human-readable alert
    details: dict            # Extra context


class ExitStrategy(ABC):
    @abstractmethod
    async def evaluate(
        self, position: Position, current_bar: dict, recent_bars: list[dict]
    ) -> ExitSignalResult | None:
        """Evaluate whether this exit condition is triggered."""
        ...
