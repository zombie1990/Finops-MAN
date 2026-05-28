from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.services.ai_agent import AIAgentService
from backend.app.security import require_permissions, AuthContext
from pydantic import BaseModel

router = APIRouter(prefix="/copilot", tags=["AI Copilot & Chat"])

class ChatRequest(BaseModel):
    conversation_id: str = None
    prompt: str

@router.get("/conversations")
def list_conversations(
    ctx: AuthContext = Depends(require_permissions("copilot:use")),
    db: Session = Depends(get_db)
):
    return AIAgentService.list_conversations(db, ctx.tenant_id)

@router.get("/history/new")
def get_new_history(
    ctx: AuthContext = Depends(require_permissions("copilot:use")),
    db: Session = Depends(get_db)
):
    return AIAgentService.get_conversation_history(db, ctx.tenant_id, None)

@router.get("/history/{conversation_id}")
def get_history(
    conversation_id: str,
    ctx: AuthContext = Depends(require_permissions("copilot:use")),
    db: Session = Depends(get_db)
):
    return AIAgentService.get_conversation_history(db, ctx.tenant_id, conversation_id)

@router.post("/chat")
def chat_with_copilot(
    request: ChatRequest,
    ctx: AuthContext = Depends(require_permissions("copilot:use")),
    db: Session = Depends(get_db)
):
    return AIAgentService.send_message(db, ctx.tenant_id, request.conversation_id, request.prompt)
