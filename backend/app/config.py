import os

class Settings:
    PROJECT_NAME: str = "FinOptica AI"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    ALLOW_ANONYMOUS_AUTH: bool = os.getenv("ALLOW_ANONYMOUS_AUTH", "true").lower() == "true"
    # false par défaut : aucune donnée fictive injectée sans action explicite
    USE_DEMO_DATA: bool = os.getenv("USE_DEMO_DATA", "false").lower() == "true"
    
    # Sécurité & JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-finops-key-for-jwt-signing-2026")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 jours
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")
    
    # Base de données
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./finoptica_dev.db")  # Utilise SQLite par défaut pour le dev rapide
    
    # Configuration Multi-Tenant
    DEFAULT_TENANT_ID: str = "tenant_enterprise_demo"
    DEFAULT_ADMIN_USERNAME: str = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "finops2026")
    DEFAULT_ADMIN_ROLE: str = os.getenv("DEFAULT_ADMIN_ROLE", "FinOps Administrator")
    
    # IA Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "mock_key")
    DEFAULT_LLM_MODEL: str = "gpt-4o"
    
    # Ingestion & Connecteurs
    INGESTION_BATCH_SIZE: int = 5000
    CACHE_EXPIRATION_SECONDS: int = 3600
    SYNC_SCHEDULER_ENABLED: bool = os.getenv("SYNC_SCHEDULER_ENABLED", "true").lower() == "true"
    SYNC_DEFAULT_INTERVAL_MINUTES: int = int(os.getenv("SYNC_DEFAULT_INTERVAL_MINUTES", "360"))

    # OIDC / SSO (Azure AD, Okta, Auth0, Keycloak)
    OIDC_ENABLED: bool = os.getenv("OIDC_ENABLED", "false").lower() == "true"
    OIDC_ISSUER: str = os.getenv("OIDC_ISSUER", "")
    OIDC_CLIENT_ID: str = os.getenv("OIDC_CLIENT_ID", "")
    OIDC_CLIENT_SECRET: str = os.getenv("OIDC_CLIENT_SECRET", "")
    OIDC_REDIRECT_URI: str = os.getenv("OIDC_REDIRECT_URI", "http://localhost:8000/api/v1/auth/oidc/callback")
    OIDC_SCOPES: str = os.getenv("OIDC_SCOPES", "openid profile email")

    # Redis (cache optionnel)
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # GitHub automation (PR remédiation)
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_REPO: str = os.getenv("GITHUB_REPO", "")  # org/repo
    GITHUB_BASE_BRANCH: str = os.getenv("GITHUB_BASE_BRANCH", "main")

settings = Settings()


def validate_security_settings() -> None:
    if settings.APP_ENV.lower() != "production":
        return

    insecure_defaults = []
    if settings.SECRET_KEY == "super-secret-finops-key-for-jwt-signing-2026":
        insecure_defaults.append("SECRET_KEY")
    if settings.DEFAULT_ADMIN_PASSWORD == "finops2026":
        insecure_defaults.append("DEFAULT_ADMIN_PASSWORD")
    if settings.OPENAI_API_KEY == "mock_key":
        insecure_defaults.append("OPENAI_API_KEY")
    if settings.ALLOW_ANONYMOUS_AUTH:
        insecure_defaults.append("ALLOW_ANONYMOUS_AUTH(false requis en production)")

    if insecure_defaults:
        raise RuntimeError(
            "Configuration securite invalide en production. Variables a corriger: "
            + ", ".join(insecure_defaults)
        )
