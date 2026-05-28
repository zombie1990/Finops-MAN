# FinOptica — Setup Enterprise Production

## 1. PostgreSQL + migrations Alembic

```bash
export DATABASE_URL="postgresql://finoptica:password@localhost:5432/finoptica"
pip install -r backend/requirements.txt
alembic upgrade head
```

## 2. Variables d'environnement complètes

```bash
export APP_ENV=production
export USE_DEMO_DATA=false
export ALLOW_ANONYMOUS_AUTH=false
export SECRET_KEY="long-random-secret"
export DATABASE_URL="postgresql://..."

# Sync automatique connecteurs (toutes les 6h par défaut)
export SYNC_SCHEDULER_ENABLED=true
export SYNC_DEFAULT_INTERVAL_MINUTES=360

# OIDC (Azure AD exemple)
export OIDC_ENABLED=true
export OIDC_ISSUER="https://login.microsoftonline.com/<TENANT_ID>/v2.0"
export OIDC_CLIENT_ID="..."
export OIDC_CLIENT_SECRET="..."
export OIDC_REDIRECT_URI="https://your-domain.com/api/v1/auth/oidc/callback"

# OpenAI RAG
export OPENAI_API_KEY="sk-..."

# GitHub PR automation
export GITHUB_TOKEN="ghp_..."
export GITHUB_REPO="org/infra-repo"
export GITHUB_BASE_BRANCH="main"

# Redis (optionnel cache)
export REDIS_URL="redis://localhost:6379/0"
```

## 3. Frontend React (web/)

```bash
cd web
npm install
npm run dev    # http://localhost:5173 (proxy API)
npm run build  # sortie dans frontend/dist
```

## 4. APIs enterprise ajoutées

| Endpoint | Description |
|----------|-------------|
| `GET /auth/oidc/login` | URL SSO |
| `GET /auth/oidc/callback` | Callback OIDC |
| `POST /copilot/rag/reindex` | Indexation RAG tenant |
| `POST /automation/github/pr/{id}` | PR GitHub remédiation |
| `GET /schedules` | Plannings sync |
| `POST /schedules` | Config intervalle sync |

## 5. Lancement production

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```
