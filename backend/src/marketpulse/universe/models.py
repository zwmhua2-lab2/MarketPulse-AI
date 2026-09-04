from pydantic import BaseModel, Field


class UniverseCandidate(BaseModel):
    symbol: str
    source: str
    priority_score: float = Field(ge=0, le=100)
    tradable: bool = True
    liquidity_ok: bool = True


class Universe(BaseModel):
    symbols: list[str]
    candidates: list[UniverseCandidate]

