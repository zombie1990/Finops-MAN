from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    username: str
    tenant_id: str
    role: str
    token: str

@router.post("/login", response_model=UserResponse)
def login(request: LoginRequest):
    # Authentification simple pour le dev de l'application SaaS
    if request.username == "admin" and request.password == "finops2026":
        return UserResponse(
            username="admin",
            tenant_id=settings.DEFAULT_TENANT_ID,
            role="FinOps Administrator",
            token="mock-jwt-token-for-enterprise-finoptica-dashboard"
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nom d'utilisateur ou mot de passe incorrect."
    )

@router.get("/me", response_model=UserResponse)
def get_me():
    return UserResponse(
        username="admin",
        tenant_id=settings.DEFAULT_TENANT_ID,
        role="FinOps Administrator",
        token="mock-jwt-token-for-enterprise-finoptica-dashboard"
    )
