from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized application settings and configuration.
    All environment variables are loaded from .env file and validated.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    # ==================== DATABASE ====================
    DATABASE_URL: str

    # ==================== JWT & AUTHENTICATION ====================
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ==================== GOOGLE OAUTH2 ====================
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None

    # ==================== EMAIL SERVICE ====================
    GOOGLE_EMAIL_FROM: str | None = None
    GOOGLE_EMAIL_PASSWORD: str | None = None

    # ==================== MINIO S3 STORAGE ====================
    MINIO_ENDPOINT: str | None = None
    MINIO_ACCESS_KEY: str | None = None
    MINIO_SECRET_KEY: str | None = None

    # ==================== STRIPE PAYMENT ====================
    STRIPE_SECRET_KEY: str | None = None

    # ==================== OCR & AI ====================
    CLAUDE_API_KEY: str | None = None

    # ==================== APPLICATION ====================
    APP_NAME: str = "Divvy API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False


settings = Settings()
