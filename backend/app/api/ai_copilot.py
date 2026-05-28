from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.models import Message
from backend.app.database import get_db
from backend.app.services.ai_agent import AIAgentService
from backend.app.services.rag_service import RagService
from backend.app.security import require_permissions, AuthContext
from typing import Optional

from pydantic import BaseModel

router = APIRouter(prefix="/copilot", tags=["AI Copilot & Chat"])

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    prompt: str
    use_rag: bool = True

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
    if request.use_rag:
        rag = RagService.answer_with_guardrails(db, ctx.tenant_id, request.prompt)
        if rag.get("grounded"):
            conv = AIAgentService.get_or_create_conversation(db, ctx.tenant_id, request.conversation_id)
            db.add(
                Message(
                    conversation_id=conv.id,
                    role="user",
                    content=request.prompt,
                    created_at=datetime.utcnow(),
                )
            )
            answer = rag["answer"] + "\n\n**Sources:** " + ", ".join(rag.get("citations", []))
            db.add(
                Message(
                    conversation_id=conv.id,
                    role="assistant",
                    content=answer,
                    created_at=datetime.utcnow(),
                    metadata_json={"type": "rag_response", "citations": rag.get("citations", [])},
                )
            )
            db.commit()
            return {
                "conversation_id": conv.id,
                "role": "assistant",
                "content": answer,
                "metadata": {"type": "rag_response", "citations": rag.get("citations", [])},
            }
    return AIAgentService.send_message(db, ctx.tenant_id, request.conversation_id, request.prompt)


@router.post("/rag/reindex")
def reindex_rag(
    ctx: AuthContext = Depends(require_permissions("copilot:use")),
    db: Session = Depends(get_db),
):
    added = RagService.index_tenant_context(db, ctx.tenant_id)
    return {"success": True, "documents_indexed": added}
