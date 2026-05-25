import os

class Settings:
    PROJECT_NAME: str = "FinOptica AI"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Sécurité & JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-finops-key-for-jwt-signing-2026")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 jours
    
    # Base de données
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./finoptica_dev.db")  # Utilise SQLite par défaut pour le dev rapide
    
    # Configuration Multi-Tenant
    DEFAULT_TENANT_ID: str = "tenant_enterprise_demo"
    
    # IA Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "mock_key")
    DEFAULT_LLM_MODEL: str = "gpt-4o"
    
    # Ingestion & Connecteurs
    INGESTION_BATCH_SIZE: int = 5000
    CACHE_EXPIRATION_SECONDS: int = 3600

settings = Settings()
