"""
🤖 Agent API Route
==================
POST /agent/chat   — multi-step ReAct agent chat
GET  /agent/steps/{book_id} — recent agent execution traces (from chat history)
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from app.service.Agent import run_agent

router = APIRouter(prefix="/agent", tags=["Agent"])


class AgentChatRequest(BaseModel):
    book_id: int = Field(..., description="ID of the processed book")
    query: str = Field(..., description="User question")
    max_steps: Optional[int] = Field(5, ge=1, le=10, description="Max reasoning steps (1-10)")


class AgentStepResponse(BaseModel):
    step: int
    thought: str
    tool: Optional[str]
    tool_input: dict
    observation: Optional[str]
    elapsed_seconds: float


class AgentChatResponse(BaseModel):
    answer: str
    sources: list
    steps: list
    similar_questions: list
    total_time: float
    query: str
    book_id: int
    agent_steps_count: int


@router.post("/chat", response_model=AgentChatResponse, summary="Chat with a book via ReAct Agent")
def agent_chat(request: AgentChatRequest):
    """
    Multi-step ReAct agent that:
    1. Checks chat history for similar past questions
    2. Searches relevant book chunks (vector + keyword)
    3. Optionally fetches book memory for broad questions
    4. Generates a grounded answer via Groq LLaMA3

    Returns the answer along with the full agent reasoning trace.
    """
    result = run_agent(
        book_id=request.book_id,
        query=request.query,
        max_steps=request.max_steps or 5,
    )

    return AgentChatResponse(
        answer=result.answer,
        sources=result.sources,
        steps=result.steps,
        similar_questions=result.similar_questions,
        total_time=result.total_time,
        query=result.query,
        book_id=result.book_id,
        agent_steps_count=len(result.steps),
    )