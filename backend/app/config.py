"""Application settings, read from environment variables (or a local .env file)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Env var names are the upper-case versions of these fields (DATABASE_URL, JWT_SECRET, ...).
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./campusbite.db"

    jwt_secret: str  # required - no default so a missing secret fails loudly at startup
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ai_rate_limit_per_minute: int = 10

    cors_origins: str = "http://localhost:5173"

    reminder_threshold_minutes: int = 15
    reminder_interval_seconds: int = 60

    seed_demo_data: bool = True
    seed_demo_password: str = "Demo@1234"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
