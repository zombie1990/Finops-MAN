# FinOptica MAN - Enterprise AI FinOps Platform

Plateforme SaaS FinOps IA orientee enterprise pour l'analyse des couts cloud, la detection de gaspillage et l'automatisation de remediations securisees.

## Etat actuel

- Backend: `FastAPI` + `SQLAlchemy`
- Frontend: application web statique JS
- Deploiement: Docker, Kubernetes, Terraform
- Donnees: SQLite en developpement (migration PostgreSQL planifiee)

## Vision enterprise

La feuille de route complete (produit, architecture, IA, securite, UX, DevOps, backlog) est decrite dans:

- `docs/enterprise-blueprint.md`

## Ameliorations deja integrees (cette iteration)

- Contexte d'authentification centralise avec token signe HMAC
- RBAC minimal par permissions (`billing:read`, `optimization:*`, `copilot:use`)
- Tenant scoping unifie dans les routes API principales
- CORS configurable via `ALLOWED_ORIGINS`
- Endpoint IA `GET /api/v1/copilot/history/new` ajoute pour coherence frontend/backend
- API connecteurs cloud (`/api/v1/connectors`) avec creation + sync + audit
- API rapports IA (`/api/v1/reports`) avec generation executive/technical/savings/carbon
- API pipeline ingestion (`/api/v1/ingestion/jobs`) avec run/retry
- API scoring de recommandations (`/api/v1/optimization/recommendations/scored`)

## Variables d'environnement

- `SECRET_KEY` (obligatoire en prod)
- `ALLOWED_ORIGINS` (liste separee par virgules)
- `APP_ENV` (`development` ou `production`)
- `ALLOW_ANONYMOUS_AUTH` (`true` en dev local, `false` en production)
- `DEFAULT_ADMIN_USERNAME`
- `DEFAULT_ADMIN_PASSWORD`
- `DEFAULT_ADMIN_ROLE`
- `DATABASE_URL`

En `production`, l'application refuse de demarrer si:
- `SECRET_KEY` est la valeur par defaut
- `DEFAULT_ADMIN_PASSWORD` est la valeur par defaut
- `OPENAI_API_KEY` est `mock_key`
- `ALLOW_ANONYMOUS_AUTH=true`

## Lancement local

```bash
./run.sh
```

Ou manuellement:

```bash
cd backend
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

## Prochaines etapes recommandees

1. Migrer SQLite vers PostgreSQL multi-tenant.
2. Ajouter CI (tests, lint, securite SAST/SCA).
3. Introduire workers d'ingestion (retry, checkpoint, rate-limit).
4. Migrer frontend vers React/TypeScript pour evolutivite enterprise.
