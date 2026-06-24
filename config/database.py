"""
PostgreSQL ulanish va sessiya sozlamalari.
SQLAlchemy ORM ishlatiladi.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/yuk_tashish_db"
)

# Engine yaratish (connection pooling bilan)
engine = create_engine(
    DATABASE_URL,
    echo=False,           # SQL loglarini ko'rish uchun True qiling
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)

# Sessiya factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Barcha modellar uchun asosiy klass."""
    pass


def get_db():
    """
    Dependency injection uchun DB sessiyasi.
    FastAPI yoki boshqa frameworklarda ishlatiladi.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Barcha jadvallarni yaratish (agar mavjud bo'lmasa)."""
    from models.zapros import Zapros          # noqa: F401
    from models.malumot import Malumot        # noqa: F401
    from models.agent_taklif import AgentTaklif  # noqa: F401
    Base.metadata.create_all(bind=engine)
    print("[DB] Barcha jadvallar muvaffaqiyatli yaratildi.")
