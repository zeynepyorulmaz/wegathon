from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import ORJSONResponse

from .schemas import ErrorResponse, ParseRequest, ParsedOutput
from .services.parser_service import parse_with_llm


app = FastAPI(
    title="Trip Prompt Parser API",
    version="0.1.0",
    default_response_class=ORJSONResponse,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.post(
    "/parse",
    response_model=ParsedOutput,
    response_model_exclude_none=True,
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "departure": {"city": "İstanbul", "country": "TR", "detected": false},
                        "destination": {"city": "Berlin", "country": "DE", "detected": true},
                        "dates": {"start_date": "2025-10-15", "end_date": "2025-10-18", "duration": 4},
                        "travelers": {"composition": "couple", "count": 2, "children": []},
                        "budget": {"amount": null, "currency": "TRY", "per_person": false, "specified": false},
                        "travel_style": {"type": "mid_range", "luxury_level": "mid_range", "tempo": "balanced"},
                        "preferences": [],
                        "special_occasions": []
                    }
                }
            }
        },
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Parse travel prompt into structured JSON",
)
def parse_endpoint(payload: ParseRequest) -> ParsedOutput:
    try:
        parsed = parse_with_llm(payload.input)
        return parsed
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health", summary="Health check")
def health() -> dict[str, str]:
    return {"status": "ok"}



