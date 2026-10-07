from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Ухаалаг математик API"
    database_url: str = "sqlite:///./dev.db"
    jwt_secret: str = "dev-secret"
    jwt_expire_minutes: int = 60
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
