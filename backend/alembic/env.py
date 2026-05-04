"""
Alembic 마이그레이션 환경 설정
SQLAlchemy 2.0 async 지원
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Alembic Config 객체
config = context.config

# Python 로깅 설정 (alembic.ini 기반)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 앱 설정 및 모델 임포트
import sys
import os

# backend/ 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import Base

# 모든 모델 임포트 (Alembic autogenerate가 인식하게)
import app.models.user  # noqa: F401
import app.models.lot   # noqa: F401

# 데이터베이스 URL을 앱 설정에서 주입
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# target_metadata: autogenerate 대상 메타데이터
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    오프라인 모드 마이그레이션 실행.
    DB 연결 없이 SQL 스크립트만 생성.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """비동기 엔진으로 마이그레이션 실행"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """온라인 모드: 실제 DB에 마이그레이션 적용"""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
