"""Зураг хадгалах (FR-03, NFR-06: хэрэглэгч устгах боломжтой).

S3/MinIO тохируулсан (`settings.s3_endpoint`) бол boto3, үгүй бол локал хавтас — хоёулаа ижил
интерфэйс: save / load / delete. Түлхүүр: "u{user_id}/{uuid}.jpg".
"""

import uuid
from pathlib import Path
from typing import Optional

from app.core.config import settings

_EXT = {"image/jpeg": ".jpg", "image/png": ".png"}


def new_key(user_id: int, content_type: str) -> str:
    return f"u{user_id}/{uuid.uuid4().hex}{_EXT.get(content_type, '.bin')}"


class LocalStorage:
    def __init__(self, root: Optional[str] = None):
        self.root = Path(root or settings.upload_dir)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root.resolve() not in p.parents:  # ../ дайралтаас сэргийлнэ
            raise ValueError("Буруу түлхүүр")
        return p

    def save(self, key: str, data: bytes, content_type: str) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def load(self, key: str) -> Optional[bytes]:
        p = self._path(key)
        return p.read_bytes() if p.exists() else None

    def delete(self, key: str) -> None:
        p = self._path(key)
        if p.exists():
            p.unlink()


class S3Storage:
    def __init__(self):
        import boto3

        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:  # noqa: BLE001 — bucket байхгүй бол үүсгэнэ
            self.client.create_bucket(Bucket=self.bucket)

    def save(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def load(self, key: str) -> Optional[bytes]:
        try:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except self.client.exceptions.NoSuchKey:
            return None

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


_storage = None


def get_storage():
    global _storage
    if _storage is None:
        _storage = S3Storage() if settings.s3_endpoint else LocalStorage()
    return _storage
