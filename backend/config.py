from functools import lru_cache
from typing import Annotated
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_anon_key: str = Field(alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(alias="SUPABASE_SERVICE_ROLE_KEY")
    agent_api_key: str = Field(alias="AGENT_API_KEY")
    cors_origins: Annotated[list[str], NoDecode] = Field(default=["http://localhost:5173"], alias="CORS_ORIGINS")
    installer_api_base_url: str | None = Field(default=None, alias="INSTALLER_API_BASE_URL")
    agent_heartbeat_interval_seconds: int = Field(default=10, ge=10, alias="AGENT_HEARTBEAT_INTERVAL_SECONDS")
    device_offline_after_seconds: int = Field(default=120, ge=60, alias="DEVICE_OFFLINE_AFTER_SECONDS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
