from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — хүснэгтүүдийг Base-д бүртгэнэ
from app.api import auth, health
from app.core.config import settings
from app.core.database import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Түр шийдэл: хүснэгтүүдийг автоматаар үүсгэнэ. Дараа нь Alembic migration руу шилжинэ.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"message": "Ухаалаг математик API ажиллаж байна", "docs": "/docs"}
