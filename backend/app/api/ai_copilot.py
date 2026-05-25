from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.services.ai_agent import AIAgentService
from backend.app.config import settings
from pydantic import BaseModel

router = APIRouter(prefix="/copilot", tags=["AI Copilot & Chat"])

class ChatRequest(BaseModel):
    conversation_id: str = None
    prompt: str

@router.get("/conversations")
def list_conversations(
    tenant_id: str = settings.DEFAULT_TENANT_ID,
    db: Session = Depends(get_db)
):
    return AIAgentService.list_conversations(db, tenant_id)

@router.get("/history/{conversation_id}")
def get_history(
    conversation_id: str,
    tenant_id: str = settings.DEFAULT_TENANT_ID,
    db: Session = Depends(get_db)
):
    return AIAgentService.get_conversation_history(db, tenant_id, conversation_id)

@router.post("/chat")
def chat_with_copilot(
    request: ChatRequest,
    tenant_id: str = settings.DEFAULT_TENANT_ID,
    db: Session = Depends(get_db)
):
    return AIAgentService.send_message(db, tenant_id, request.conversation_id, request.prompt)
