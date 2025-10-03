from fastapi import APIRouter, HTTPException
from typing import Dict, List
from app.models.plan import PlanRequest, ReviseRequest, TripPlan
from app.services.planner import generate, revise
from app.services.ask import ask_questions

router = APIRouter(prefix="/api", tags=["planner"])


@router.post("/plan", response_model=TripPlan)
async def plan_endpoint(req: PlanRequest):
    try:
        return await generate(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/revise", response_model=TripPlan)
async def revise_endpoint(payload: Dict):
    try:
        plan = payload.get("plan")
        req = ReviseRequest(planId=payload.get("planId", ""), instruction=payload["instruction"])  # type: ignore
        return await revise(plan, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask_questions")
async def ask_endpoint(history: List[Dict]):
    try:
        content = await ask_questions(history)
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

