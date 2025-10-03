from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers.plan import router as api_router

app = FastAPI(title="Trip Planner Backend", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list() or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}

