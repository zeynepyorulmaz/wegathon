from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class Departure(BaseModel):
    city: str
    country: str
    detected: bool


class Destination(BaseModel):
    city: str
    country: str
    detected: bool


class Child(BaseModel):
    age: int


class Travelers(BaseModel):
    composition: Optional[str] = None
    count: Optional[int] = None
    children: Optional[List[Child]] = None


class Dates(BaseModel):
    start_date: Optional[str] = None
    duration: Optional[int] = None
    end_date: Optional[str] = None
    flexible: Optional[bool] = None


class Budget(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = Field(default=None, description="ISO currency code, default TRY if missing")
    per_person: Optional[bool] = None
    specified: Optional[bool] = None


class TravelStyle(BaseModel):
    type: Optional[str] = None
    luxury_level: Optional[str] = None
    tempo: Optional[str] = None


class ParsedOutput(BaseModel):
    departure: Departure
    destination: Destination
    dates: Dates
    travelers: Travelers
    budget: Budget
    travel_style: TravelStyle
    preferences: List[Any]
    special_occasions: List[Any]

    model_config = {
        "extra": "allow"  # allow future compatible fields without failing validation
    }


class ParseRequest(BaseModel):
    input: str = Field(..., description="User natural language travel request to parse")
    locale: Optional[str] = Field(default="tr-TR", description="Locale hint, default tr-TR")


class ErrorResponse(BaseModel):
    detail: str
    raw_response: Optional[str] = None


