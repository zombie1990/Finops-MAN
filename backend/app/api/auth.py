from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.app.config import settings
from backend.app.security import create_access_token, get_auth_context, AuthContext

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
    # Authentification locale (dev/staging) pilotée par variables d'environnement.
    if request.username == settings.DEFAULT_ADMIN_USERNAME and request.password == settings.DEFAULT_ADMIN_PASSWORD:
        token = create_access_token(
            username=settings.DEFAULT_ADMIN_USERNAME,
            tenant_id=settings.DEFAULT_TENANT_ID,
            role=settings.DEFAULT_ADMIN_ROLE,
        )
        return UserResponse(
            username=settings.DEFAULT_ADMIN_USERNAME,
            tenant_id=settings.DEFAULT_TENANT_ID,
            role=settings.DEFAULT_ADMIN_ROLE,
            token=token,
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nom d'utilisateur ou mot de passe incorrect."
    )

@router.get("/me", response_model=UserResponse)
def get_me(ctx: AuthContext = Depends(get_auth_context)):
    return UserResponse(
        username=ctx.username,
        tenant_id=ctx.tenant_id,
        role=ctx.role,
        token=ctx.token,
    )
