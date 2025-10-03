from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class RequiredField(BaseModel):
    """A field that needs to be collected from the user"""
    field: str
    question: str
    type: str  # "text", "date", "number", "choice"
    options: Optional[List[str]] = None
    example: Optional[str] = None


class ConversationState(BaseModel):
    """State of the conversation for collecting trip requirements"""
    session_id: str
    original_prompt: str
    collected_data: Dict[str, Any] = {}
    remaining_fields: List[RequiredField] = []
    current_question: Optional[RequiredField] = None
    ready_to_plan: bool = False


class QuestionResponse(BaseModel):
    """Response asking user for more information"""
    message: str
    question: RequiredField
    session_id: str
    collected_so_far: Dict[str, Any]


class UserAnswer(BaseModel):
    """User's answer to a question"""
    session_id: str
    answer: Any

