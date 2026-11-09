from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class RawArticle(BaseModel):
    title: str = Field(min_length=1, max_length=1000)
    body: str = Field(min_length=1, max_length=200000)
    url: HttpUrl
    source: str
    published_at: datetime | None = None
    data_mode: Literal["live", "demo"] = "live"
    fetched_at: datetime

    @field_validator("published_at", "fetched_at")
    @classmethod
    def aware_dates(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("datetime requires timezone")
        return value


class EvidenceFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text_zh: str
    quote: str = Field(min_length=1)


class LLMAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title_zh: str
    facts: list[EvidenceFact] = Field(min_length=1, max_length=10)
    potential_impacts: list[str]
    watch_indicators: list[str]
    suggested_actions: list[str]
