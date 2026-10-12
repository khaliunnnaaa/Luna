from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[3]  # Luna/ (backend/app/core/config.py)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Ухаалаг математик API"
    # Локалд PostgreSQL-гүйгээр SQLite файл ашиглана. Docker дээр .env-ээс PostgreSQL авна.
    database_url: str = "sqlite:///./dev.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    # BKT параметр (ML хэсэг сургасан). Байхгүй бол services/mastery.py-ийн анхдагч утга.
    bkt_params_path: str = str(_ROOT / "ml" / "config" / "bkt_params.yaml")

    # ML сервис (ml/service.py). Хоосон/холбогдохгүй бол OCR, ангилалгүй гараар бичнэ (NFR-07).
    ml_service_url: str = "http://localhost:8001"
    ml_timeout_seconds: float = 20.0

    # Зураг хадгалах: S3/MinIO тохируулсан бол тийшээ, үгүй бол локал хавтас (dev).
    s3_endpoint: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "uploads"
    s3_region: str = "us-east-1"  # MinIO-д хамаагүй; Supabase Storage-д төслийн region
    upload_dir: str = str(_ROOT / "backend" / "uploads")
    max_upload_bytes: int = 10 * 1024 * 1024


settings = Settings()
