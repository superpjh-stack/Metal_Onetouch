"""DB 호환 패치

- TIMESTAMPTZ: SQLAlchemy pg dialect에 없음 → DateTime(timezone=True)로 주입 (PostgreSQL/SQLite 공통)
- JSONB: SQLite 사용 시에만 JSON으로 대체
"""
import sqlalchemy.dialects.postgresql as _pg
from sqlalchemy import DateTime, JSON

# TIMESTAMPTZ는 SQLAlchemy pg dialect에 미노출 → 항상 주입
if not hasattr(_pg, "TIMESTAMPTZ"):
    _pg.TIMESTAMPTZ = DateTime(timezone=True)  # type: ignore[attr-defined]

# SQLite 사용 시 JSONB → JSON 대체
from app.core.config import settings

if settings.DATABASE_URL.startswith("sqlite"):
    _pg.JSONB = JSON  # type: ignore[attr-defined]
