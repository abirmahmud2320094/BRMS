from functools import lru_cache
from typing import List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BRMS API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"

    cors_origins: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    auth_mode: str = "firebase"
    data_mode: str = "firebase"

    local_data_path: str = "data/local_data.json"

    firebase_project_id: Optional[str] = None
    google_application_credentials: Optional[str] = None
    firebase_service_account_json: Optional[str] = None
    firebase_operation_timeout_seconds: float = Field(default=5.0, ge=1.0, le=30.0)

    seed_admin_email: str = "admin@brms.local"
    seed_admin_password: str = "ChangeMe123!"
    seed_admin_name: str = "BRMS Administrator"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, value):
        if isinstance(value, str):
            return [
                item.strip()
                for item in value.split(",")
                if item.strip()
            ]

        return value

    @field_validator("auth_mode")
    @classmethod
    def validate_auth_mode(cls, value):
        value = value.lower()
        if value not in {"demo", "firebase"}:
            raise ValueError("AUTH_MODE must be 'demo' or 'firebase'")
        return value

    @field_validator("data_mode")
    @classmethod
    def validate_data_mode(cls, value):
        value = value.lower()
        if value not in {"local", "firebase"}:
            raise ValueError("DATA_MODE must be 'local' or 'firebase'")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
