from typing import List, Dict
from app.services.openai_client import chat

SYSTEM = (
    "You are Trip Planner assistant. Ask clarifying questions when needed and answer concisely. "
    "When querying museum hours or local facts, provide best-effort info and suggest verifying links if unsure."
)


async def ask_questions(history: List[Dict]) -> str:
    messages = [{"role": "system", "content": SYSTEM}] + history
    return await chat(messages)

