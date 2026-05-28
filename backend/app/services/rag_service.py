import math
import re
import uuid
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models import RagDocument, Recommendation, CostItem, Anomaly
from backend.app.services.ai_agent import AIAgentService


class RagService:
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [t for t in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(t) > 2]

    @staticmethod
    def _embed(text: str) -> Dict[str, float]:
        tokens = RagService._tokenize(text)
        vec: Dict[str, float] = {}
        for token in tokens:
            vec[token] = vec.get(token, 0.0) + 1.0
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {k: v / norm for k, v in vec.items()}

    @staticmethod
    def _similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
        return sum(a.get(k, 0) * b.get(k, 0) for k in set(a) | set(b))

    @staticmethod
    def seed_tenant_knowledge(db: Session, tenant_id: str) -> None:
        if db.query(RagDocument).filter(RagDocument.tenant_id == tenant_id).count() > 0:
            return
        for key, content in AIAgentService.KNOWLEDGE_BASE.items():
            doc = RagDocument(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                source="finops_kb",
                title=key,
                content=content,
                embedding_json=RagService._embed(content),
            )
            db.add(doc)
        db.commit()

    @staticmethod
    def index_tenant_context(db: Session, tenant_id: str) -> int:
        RagService.seed_tenant_knowledge(db, tenant_id)
        (
            db.query(RagDocument)
            .filter(
                RagDocument.tenant_id == tenant_id,
                RagDocument.source == "recommendation",
            )
            .delete(synchronize_session=False)
        )
        added = 0
        recs = db.query(Recommendation).filter(Recommendation.tenant_id == tenant_id).limit(20).all()
        for rec in recs:
            content = f"{rec.recommendation_type} {rec.resource_name} saving {rec.estimated_saving}"
            db.add(
                RagDocument(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    source="recommendation",
                    title=rec.id,
                    content=content,
                    embedding_json=RagService._embed(content),
                )
            )
            added += 1
        db.commit()
        return added

    @staticmethod
    def retrieve(db: Session, tenant_id: str, query: str, top_k: int = 4) -> List[Dict]:
        RagService.seed_tenant_knowledge(db, tenant_id)
        query_vec = RagService._embed(query)
        docs = db.query(RagDocument).filter(RagDocument.tenant_id == tenant_id).all()
        scored = []
        for doc in docs:
            emb = doc.embedding_json or RagService._embed(doc.content)
            score = RagService._similarity(query_vec, emb)
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "title": doc.title,
                "source": doc.source,
                "content": doc.content[:500],
                "score": round(score, 3),
            }
            for score, doc in scored[:top_k]
            if score > 0
        ]

    @staticmethod
    def _call_openai(system_prompt: str, user_prompt: str) -> Optional[str]:
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "mock_key":
            return None
        try:
            import httpx

            payload = {
                "model": settings.DEFAULT_LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
            }
            with httpx.Client(timeout=45.0) as client:
                res = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    json=payload,
                )
                res.raise_for_status()
                return res.json()["choices"][0]["message"]["content"]
        except Exception:
            return None

    @staticmethod
    def answer_with_guardrails(db: Session, tenant_id: str, prompt: str) -> Dict:
        contexts = RagService.retrieve(db, tenant_id, prompt, top_k=5)
        if not contexts:
            return {
                "answer": "Je n'ai pas encore assez de contexte indexé. Connectez un cloud ou importez un CSV.",
                "citations": [],
                "grounded": False,
            }

        citations = [f"[{c['source']}] {c['title']}" for c in contexts]
        context_block = "\n\n".join([f"- {c['content']}" for c in contexts])
        system_prompt = (
            "Tu es FinOptica Copilot. Réponds uniquement avec les faits du contexte fourni. "
            "Si une information manque, dis-le explicitement. Ne fabrique pas de chiffres."
        )
        user_prompt = f"Contexte:\n{context_block}\n\nQuestion:\n{prompt}"

        llm_answer = RagService._call_openai(system_prompt, user_prompt)
        if llm_answer:
            return {
                "answer": llm_answer,
                "citations": citations,
                "grounded": True,
                "llm_used": True,
            }

        # Fallback sans LLM: synthèse factuelle
        summary = (
            f"Analyse basée sur {len(contexts)} sources indexées.\n\n"
            + "\n".join([f"* **{c['title']}** ({c['source']}): {c['content'][:180]}..." for c in contexts])
        )
        return {
            "answer": summary,
            "citations": citations,
            "grounded": False,
            "llm_used": False,
        }
