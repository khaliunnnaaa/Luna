from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Ухаалаг математик API"
    # Локалд PostgreSQL-гүйгээр SQLite файл ашиглана. Docker дээр .env-ээс PostgreSQL авна.
    database_url: str = "sqlite:///./dev.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


settings = Settings()
