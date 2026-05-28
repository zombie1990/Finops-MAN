# Passage en données réelles (Production)

## 1. Désactiver le mode sandbox

Par défaut, `USE_DEMO_DATA=false` (aucune donnée fictive injectée).

Ne l'activez que pour des démos locales explicites:

```bash
export USE_DEMO_DATA=true
```

## 2. Connecter AWS (Cost Explorer)

Dans **Paramètres > Connexions Cloud**, ajoutez:

```json
{
  "access_key_id": "AKIA...",
  "secret_access_key": "...",
  "region": "eu-west-3",
  "account_id": "123456789012"
}
```

Permissions IAM minimales: `ce:GetCostAndUsage`, `ce:GetDimensionValues`.

Puis cliquez **Tester** puis **Synchroniser**.

## 3. Connecter Azure (Cost Management)

```json
{
  "tenant_id": "...",
  "client_id": "...",
  "client_secret": "...",
  "subscription_id": "..."
}
```

Rôle recommandé: `Cost Management Reader`.

## 4. Connecter GCP (BigQuery Billing Export)

Prérequis: activer l'export billing vers BigQuery.

```json
{
  "project_id": "my-project",
  "service_account_json": { "...": "..." },
  "bigquery_dataset": "billing_export",
  "bigquery_table": "gcp_billing_export_v1"
}
```

## 5. Import CSV manuel

Colonnes obligatoires: `date`, `provider`, `service`, `cost`.

Colonnes optionnelles: `account_id`, `resource_id`, `resource_name`, `region`.

## 6. Variables production recommandées

```bash
export APP_ENV=production
export USE_DEMO_DATA=false
export ALLOW_ANONYMOUS_AUTH=false
export SECRET_KEY="long-random-secret"
export DATABASE_URL="postgresql://user:pass@host:5432/finoptica"
```

## 7. Prochaines étapes architecture

- PostgreSQL managé + Alembic migrations
- Workers async (ingestion planifiée)
- OIDC SSO (Azure AD/Okta)
- Frontend React/Next.js
- Observabilité OpenTelemetry
