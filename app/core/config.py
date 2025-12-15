from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator
import secrets


class Settings(BaseSettings):
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "RealEstate Platform"

    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Add to Settings class

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None
    CLOUDINARY_UPLOAD_PRESET: str = "imobplan_properties"

    # Geocoding (choose one)
    MAPBOX_ACCESS_TOKEN: Optional[str] = None
    GOOGLE_MAPS_API_KEY: Optional[str] = None

    # Property settings
    MAX_PHOTOS_PER_PROPERTY: int = 20
    LISTING_EXPIRY_DAYS: int = 60
    REFRESH_COOLDOWN_HOURS: int = 24

    REDIS_URL: str = "redis://redis:6379/0"
    CACHE_ENABLED: bool = True
    SEARCH_CACHE_TTL: int = 300
    PROPERTY_CACHE_TTL: int = 3600

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()