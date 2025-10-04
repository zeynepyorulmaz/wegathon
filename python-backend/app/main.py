from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.routers.plan import router as api_router
from app.services.mcp_pool import initialize_mcp_pool, get_mcp_pool
from app.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - startup and shutdown."""
    # Startup
    logger.info("🚀 Starting AIKU Travel Planner API...")
    try:
        await initialize_mcp_pool()
        logger.info("✅ MCP Session Pool initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize MCP pool: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down AIKU Travel Planner API...")
    try:
        pool = get_mcp_pool()
        await pool.shutdown()
        logger.info("✅ MCP Session Pool shutdown complete")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")


app = FastAPI(
    title="AIKU - AI Travel Planner API",
    version="2.0.0",
    lifespan=lifespan,
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
    Simple health check endpoint with MCP pool and cache stats.
    
    Returns:
        - **status**: "ok" if the service is running
        - **mcp_pool**: Connection pool statistics
        - **cache**: Cache statistics
    """
    try:
        pool = get_mcp_pool()
        pool_stats = await pool.get_stats()
    except Exception as e:
        pool_stats = {"error": str(e)}
    
    try:
        from app.services.cache_service import get_cache
        cache = get_cache()
        cache_stats = cache.get_stats()
    except Exception as e:
        cache_stats = {"error": str(e)}
    
    return {
        "status": "ok",
        "version": "2.0.0",
        "service": "AIKU Travel Planner",
        "mcp_pool": pool_stats,
        "cache": cache_stats
    }

