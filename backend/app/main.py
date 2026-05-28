from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from backend.app.config import settings, validate_security_settings
from backend.app.database import engine, Base
from backend.app.api import auth, billing, optimization, ai_copilot, connectors, reports, ingestion, platform, csv_io, automation, schedules
from backend.app.workers.scheduler import start_scheduler, stop_scheduler

# Initialiser la base de données (crée les tables si inexistantes)
validate_security_settings()
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="SaaS Enterprise FinOps piloté par l'Intelligence Artificielle",
    lifespan=lifespan,
)

# Configurer les CORS pour le développement
allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enregistrer les routers API sous /api/v1
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(billing.router, prefix=settings.API_V1_STR)
app.include_router(optimization.router, prefix=settings.API_V1_STR)
app.include_router(ai_copilot.router, prefix=settings.API_V1_STR)
app.include_router(connectors.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(ingestion.router, prefix=settings.API_V1_STR)
app.include_router(platform.router, prefix=settings.API_V1_STR)
app.include_router(csv_io.router, prefix=settings.API_V1_STR)
app.include_router(automation.router, prefix=settings.API_V1_STR)
app.include_router(schedules.router, prefix=settings.API_V1_STR)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.PROJECT_NAME, "env": settings.APP_ENV}

# Servir l'application Frontend statique
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))

if os.path.exists(frontend_dir):
    # Route spécifique pour servir l'index.html à la racine
    @app.get("/")
    def read_index():
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "FinOptica API is running. Frontend build files not found."}
    
    # Monter le reste des fichiers statiques (CSS, JS, etc.)
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    @app.get("/")
    def read_root():
        return {
            "message": "FinOptica API is running.",
            "documentation": "/docs",
            "frontend_status": "Directory 'frontend/' not found at workspace root."
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
