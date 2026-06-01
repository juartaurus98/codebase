from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "python-toolkit"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group_id: str = "python-toolkit-group"
    kafka_audit_topic: str = "audit.requests"
    kafka_producer_acks: str = "all"
    kafka_producer_retries: int = 3

    # Logging
    log_level: str = "INFO"
    log_json: bool = True

    # Database Backend Selection
    db_backend: str = "postgres"  # "postgres" | "mongodb" | "redis"

    # PostgreSQL
    postgres_url: str = "postgresql+asyncpg://user:password@localhost/python_toolkit"

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "python_toolkit"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600

    # Gemini
    gemini_api_key: str = ""
    gemini_default_model: str = "gemini-2.0-flash"
    gemini_timeout_seconds: int = 60

    # OpenAI
    openai_api_key: str = ""
    openai_default_model: str = "gpt-4o"
    openai_timeout_seconds: int = 60

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
