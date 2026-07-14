"""
Chat Routes
"""
from fastapi import APIRouter
from pydantic import BaseModel
from src.engine.orchestrator import SimulationOrchestrator

router = APIRouter()
orchestrator = SimulationOrchestrator()

class ChatRequest(BaseModel):
    user_id: str
    target_persona: str
    message: str

class ChatResponse(BaseModel):
    message: str
    state_update: dict
    safety_flags: list
    metadata: dict

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    response = await orchestrator.handle_message(
        request.user_id,
        request.target_persona,
        request.message
    )
    return ChatResponse(
        message=response.message,
        state_update=response.state_update,
        safety_flags=response.safety_flags,
        metadata=response.metadata
    )

@router.get("/personas")
async def get_personas():
    return [
        {"id": "gucci_ceo", "name": "Marco Bianchi (CEO)"},
        {"id": "gucci_chro", "name": "Elena Rossi (CHRO)"},
        {"id": "regional_manager", "name": "Thomas Nguyen (RM)"}
    ]
