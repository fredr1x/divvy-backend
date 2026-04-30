from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None

    GOOGLE_EMAIL_FROM: str | None = None
    GOOGLE_EMAIL_PASSWORD: str | None = None

    MINIO_ENDPOINT: str | None = None
    MINIO_ACCESS_KEY: str | None = None
    MINIO_SECRET_KEY: str | None = None

    STRIPE_SECRET_KEY: str | None = None

    CLAUDE_API_KEY: str | None = None
    CLAUDE_MODEL_ID: str | None = None
    CLAUDE_MAX_TOKENS: int | None = None

    APP_NAME: str = "Divvy API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    BACKEND_DOMAIN: str | None = "http://localhost:8001"
    FRONTEND_DOMAIN: str | None = "http://localhost:3000"

settings = Settings()
