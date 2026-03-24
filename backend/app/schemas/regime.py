from datetime import datetime

from pydantic import BaseModel


class RegimeResponse(BaseModel):
    id: int
    regime: str
    confidence: float
    previous_regime: str | None = None
    detection_method: str = "hmm"
    features: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RegimeHistoryResponse(BaseModel):
    current: RegimeResponse
    history: list[RegimeResponse]
