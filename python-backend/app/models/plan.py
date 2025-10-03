from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any


class SourceRef(BaseModel):
    provider: str
    id: Optional[str] = None
    url: Optional[str] = None


class ToolDiag(BaseModel):
    tool: str
    ok: bool
    ms: Optional[int] = None
    error: Optional[str] = None


class FlightSegment(BaseModel):
    fromIata: str
    toIata: str
    departISO: str
    arriveISO: str
    airline: str
    flightNumber: str
    durationMinutes: int
    cabin: Optional[str] = None


class FlightOption(BaseModel):
    provider: str
    price: Optional[float] = None
    currency: Optional[str] = None
    segments: List[FlightSegment]
    baggage: Optional[str] = None
    refundable: Optional[bool] = None
    bookingUrl: Optional[str] = None


class HotelOption(BaseModel):
    provider: str
    name: str
    address: Optional[str] = None
    checkInISO: str
    checkOutISO: str
    priceTotal: Optional[float] = None
    currency: Optional[str] = None
    rating: Optional[float] = None
    amenities: Optional[List[str]] = None
    neighborhood: Optional[str] = None
    bookingUrl: Optional[str] = None


class TransportPass(BaseModel):
    name: str
    price: Optional[float] = None
    currency: Optional[str] = None
    coverageNotes: Optional[str] = None
    url: Optional[str] = None


class IntercityLeg(BaseModel):
    mode: Literal["bus", "train"]
    from_: str = Field(alias="from")
    to: str
    departISO: str
    arriveISO: str
    price: Optional[float] = None
    currency: Optional[str] = None
    operator: Optional[str] = None
    url: Optional[str] = None

    class Config:
        populate_by_name = True


class Activity(BaseModel):
    provider: str
    title: str
    startISO: Optional[str] = None
    endISO: Optional[str] = None
    durationMinutes: Optional[int] = None
    category: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    bookingUrl: Optional[str] = None
    notes: Optional[str] = None


class TransferData(BaseModel):
    mode: Literal["walk", "metro", "bus", "car", "train"]
    from_: str = Field(alias="from")
    to: str
    minutes: int
    notes: Optional[str] = None

    class Config:
        populate_by_name = True


class BufferData(BaseModel):
    minutes: int
    reason: str


class BlockItem(BaseModel):
    type: Literal["flight", "lodging", "activity", "transfer", "buffer"]
    data: Dict[str, Any]


class DayBlock(BaseModel):
    label: Literal["morning", "afternoon", "evening", "late-night", "transit", "check-in", "check-out"]
    items: List[BlockItem]
    notes: Optional[str] = None


class DayPlan(BaseModel):
    dateISO: str
    blocks: List[DayBlock]
    dailyTips: Optional[List[str]] = None


class DailyWeather(BaseModel):
    dateISO: str
    highC: Optional[float] = None
    lowC: Optional[float] = None
    precipitationChance: Optional[float] = None
    source: str
    isForecast: bool


class FlightsSection(BaseModel):
    outbound: Optional[FlightOption] = None
    inbound: Optional[FlightOption] = None
    alternatives: Optional[List[FlightOption]] = None


class LodgingSection(BaseModel):
    selected: Optional[HotelOption] = None
    alternatives: Optional[List[HotelOption]] = None


class TransportSection(BaseModel):
    localPasses: Optional[List[TransportPass]] = None
    intercity: Optional[List[IntercityLeg]] = None


class PricingBreakdown(BaseModel):
    flights: Optional[float] = None
    lodging: Optional[float] = None
    activities: Optional[float] = None
    transport: Optional[float] = None
    feesAndTaxes: Optional[float] = None


class Pricing(BaseModel):
    currency: str
    breakdown: PricingBreakdown
    totalEstimated: Optional[float] = None
    confidence: Literal["low", "medium", "high"]
    notes: Optional[List[str]] = None


class ParsedQuery(BaseModel):
    originCity: str
    originIata: Optional[str] = None
    destinationCity: str
    destinationIata: Optional[str] = None
    startDateISO: str
    endDateISO: str
    nights: int
    adults: int
    children: Optional[int] = None
    budget: Optional[Dict[str, Any]] = None
    preferences: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    language: Optional[str] = None
    currency: Optional[str] = None


class Query(BaseModel):
    raw: str
    parsed: ParsedQuery


class Metadata(BaseModel):
    generatedAtISO: str
    sources: List[SourceRef]
    toolDiagnostics: Optional[List[ToolDiag]] = None
    warnings: Optional[List[str]] = None
    revisionOf: Optional[str] = None
    planId: str


class TripPlan(BaseModel):
    query: Query
    summary: str
    flights: FlightsSection
    lodging: LodgingSection
    transport: TransportSection
    weather: List[DailyWeather]
    days: List[DayPlan]
    pricing: Pricing
    metadata: Metadata


class PlanRequest(BaseModel):
    prompt: str
    currency: Optional[str] = None
    language: Optional[str] = None


class ReviseRequest(BaseModel):
    planId: str
    instruction: str
    # The planner will fetch the previous plan (DB or caller-provided in practice)

