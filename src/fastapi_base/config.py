from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "FastAPI Base"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@db:5432/fastapi_base",
        validation_alias="DATABASE_URL",
    )

    # JWT
    jwt_secret: str = Field(
        default="dev-secret-key-change-in-production",
        validation_alias="JWT_SECRET",
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Cookies
    cookie_secure: bool = False  # Set to True in production (HTTPS)
    cookie_samesite: str | None = "lax"  # lax | strict | none

    # CORS
    cors_origins: str = ""  # Comma-separated list of origins

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins:
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # Helper to convert sync database URL to async if needed
    @property
    def to_async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()