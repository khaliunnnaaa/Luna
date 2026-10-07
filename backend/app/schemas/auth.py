import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import Role

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)
    role: Role = Role.student

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Имэйл хаяг буруу байна")
        return v

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Нэрээ оруулна уу")
        return v

    @field_validator("role")
    @classmethod
    def no_self_admin(cls, v: Role) -> Role:
        # Админ эрхийг өөрөө бүртгүүлж авах боломжгүй (scripts-ээр үүсгэнэ)
        if v == Role.admin:
            raise ValueError("Админ эрхээр бүртгүүлэх боломжгүй")
        return v


class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize(cls, v: str) -> str:
        return v.strip().lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: Role
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
