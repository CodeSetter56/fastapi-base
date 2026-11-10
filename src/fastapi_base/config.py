from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "FastAPI Base"

    # Database
    database_url: str = Field(validation_alias="DATABASE_URL")

    # JWT
    jwt_secret: str = Field(validation_alias="JWT_SECRET",)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Cookies
    cookie_samesite: str | None = "lax"
    cookie_secure: bool = False # true during production 
    cors_origins: str = ""

    # OAuth
    google_client_id: str = Field(default="", validation_alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", validation_alias="GOOGLE_CLIENT_SECRET")

    # S3 / MinIO Storage
    s3_endpoint_url: str | None = Field(default=None, validation_alias="S3_ENDPOINT_URL")
    s3_access_key_id: str = Field(default="minioadmin", validation_alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str = Field(default="minioadmin", validation_alias="S3_SECRET_ACCESS_KEY")
    s3_bucket_name: str = Field(default="uploads", validation_alias="S3_BUCKET_NAME")
    s3_region_name: str = Field(default="us-east-1", validation_alias="S3_REGION_NAME")

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins:
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def to_async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()  # pyright: ignore[reportCallIssue]
