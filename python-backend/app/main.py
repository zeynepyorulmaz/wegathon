from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers.plan import router as api_router

app = FastAPI(
    title="AIKU - AI Travel Planner API",
    version="1.0.0",
    description="""
## 🌍 AI-Powered Travel Planning System

Complete travel planning solution with conversational AI, MCP integration, and interactive itineraries.

### Features

* 🤖 **Conversational Planning** - AI collects trip details through natural conversation
* ✈️ **Real MCP Data** - Live flight, hotel, weather, and bus information
* 🎯 **Interactive Plans** - Multiple activity options for each time slot
* 🔄 **Plan Revision** - Modify plans with natural language requests
* 🌐 **Multi-language** - Turkish and English support

### Quick Start

1. **Simple Plan**: POST `/api/plan` with your travel prompt
2. **Conversational**: Start with POST `/api/chat/start` for guided experience
3. **Interactive Format**: Use POST `/api/plan/interactive` for frontend-ready options

### Documentation

- Swagger UI: [/docs](/docs) (you are here)
- ReDoc: [/redoc](/redoc)
- OpenAPI JSON: [/openapi.json](/openapi.json)
    """,
    contact={
        "name": "AIKU Team",
        "email": "support@aiku.com",
    },
    license_info={
        "name": "Private",
    },
    openapi_tags=[
        {
            "name": "Planning",
            "description": "Core trip planning endpoints - create and revise travel plans",
        },
        {
            "name": "Conversation",
            "description": "AI-driven conversational planning with automatic information collection",
        },
        {
            "name": "Tools",
            "description": "MCP tool management and discovery",
        },
        {
            "name": "Utilities",
            "description": "Parsing and helper endpoints",
        },
        {
            "name": "Health",
            "description": "System health and status checks",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list() or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Check if the API is running and responsive",
    response_description="API health status"
)
async def health():
    """
    Simple health check endpoint.
    
    Returns:
        - **status**: "ok" if the service is running
    """
    return {"status": "ok", "version": "1.0.0", "service": "AIKU Travel Planner"}

