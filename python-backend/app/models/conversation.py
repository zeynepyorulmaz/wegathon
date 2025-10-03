"""
Conversational trip planning models - manages chat sessions and plan evolution.
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class ChatMessage(BaseModel):
    """A single message in the conversation."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ConversationSession(BaseModel):
    """
    Complete conversation session with history and current plan.
    Tracks the evolution of trip planning through conversation.
    """
    session_id: str
    messages: List[ChatMessage] = []
    collected_data: Dict[str, Any] = {}  # Parsed trip information
    current_plan: Optional[Dict[str, Any]] = None  # Latest generated plan
    ready_to_plan: bool = False  # Has enough info to create plan
    plan_created: bool = False  # Has a plan been created yet
    
    
class ChatStartRequest(BaseModel):
    """Request to start a new conversation."""
    initial_message: str = Field(..., description="User's initial travel request")
    language: str = Field(default="tr", description="Response language (tr/en)")
    currency: str = Field(default="TRY", description="Currency for pricing")


class ChatContinueRequest(BaseModel):
    """Request to continue an existing conversation."""
    session_id: str = Field(..., description="Conversation session ID")
    message: str = Field(..., description="User's message")


class ChatResponse(BaseModel):
    """Response from the conversation system."""
    session_id: str
    message: str  # AI's response message
    plan: Optional[Dict[str, Any]] = None  # Current plan if available
    collected_data: Dict[str, Any] = {}  # What we know so far
    needs_more_info: bool = False  # Waiting for more user input
    conversation_complete: bool = False  # Plan finalized, no more questions

