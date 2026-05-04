"""
초기 관리자 계정 및 기준 코드 데이터 시딩 스크립트

사용법:
    cd backend
    python -m scripts.seed_master_data
    또는
    python scripts/seed_master_data.py
"""
import asyncio
import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import hash_password
from app.models.user import User
from app.models.lot import Lot, LotHistory


# ------------------------------------------------------------------------------
# 초기 사용자 데이터
# ------------------------------------------------------------------------------
INITIAL_USERS = [
    {
        "email": "admin@onetouch.com",
        "password": "Admin1234!",
        "full_name": "시스템 관리자",
        "role": "admin",
        "department": "IT",
        "status": "active",
        "is_superuser": True,
    },
    {
        "email": "production@onetouch.com",
        "password": "Prod1234!",
        "full_name": "김생산",
        "role": "production_manager",
        "department": "생산팀",
        "status": "active",
        "is_superuser": False,
    },
    {
        "email": "quality@onetouch.com",
        "password": "Qual1234!",
        "full_name": "이품질",
        "role": "quality_inspector",
        "department": "품질팀",
        "status": "active",
        "is_superuser": False,
    },
    {
        "email": "engineer@onetouch.com",
        "password": "Eng1234!",
        "full_name": "박공정",
        "role": "process_engineer",
        "department": "공정팀",
        "status": "active",
        "is_superuser": False,
    },
    {
        "email": "executive@onetouch.com",
        "password": "Exec1234!",
        "full_name": "최임원",
        "role": "executive",
        "department": "경영진",
        "status": "active",
        "is_superuser": False,
    },
    {
        "email": "sales@onetouch.com",
        "password": "Sales1234!",
        "full_name": "정영업",
        "role": "sales_engineer",
        "department": "영업팀",
        "status": "active",
        "is_superuser": False,
    },
]


async def create_tables() -> None:
    """테이블 생성 (Alembic 없이 직접 생성 - 개발 전용)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] 테이블 생성 완료")


async def seed_users(session: AsyncSession) -> list[User]:
    """초기 사용자 계정 생성"""
    created_users = []

    for user_data in INITIAL_USERS:
        # 기존 계정 확인
        result = await session.execute(
            select(User).where(User.email == user_data["email"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  [SKIP] 이미 존재: {user_data['email']}")
            created_users.append(existing)
            continue

        user = User(
            email=user_data["email"],
            hashed_password=hash_password(user_data["password"]),
            full_name=user_data["full_name"],
            role=user_data["role"],
            department=user_data["department"],
            status=user_data["status"],
            is_superuser=user_data["is_superuser"],
        )
        session.add(user)
        created_users.append(user)
        print(f"  [CREATE] {user_data['email']} ({user_data['role']})")

    await session.flush()
    return created_users


async def seed_sample_lots(session: AsyncSession, created_by_user: User) -> None:
    """샘플 LOT 데이터 생성"""
    sample_lots = [
        {
            "lot_id": "L20260430-0001",
            "lot_status": "in_process",
            "raw_material_id": "RM-SUS304-001",
            "raw_material_name": "SUS304 판재 2.0T",
            "quantity": 500.0,
            "unit": "kg",
            "customer_name": "삼성전자(주)",
            "product_code": "PROD-SE-001",
            "product_name": "프레스 판금 부품 A형",
            "order_number": "ORD-20260430-001",
        },
        {
            "lot_id": "L20260430-0002",
            "lot_status": "in_inspection",
            "raw_material_id": "RM-AL6061-001",
            "raw_material_name": "알루미늄 6061 봉재",
            "quantity": 200.0,
            "unit": "kg",
            "customer_name": "LG전자(주)",
            "product_code": "PROD-LG-002",
            "product_name": "CNC 선반 가공품 B형",
            "order_number": "ORD-20260430-002",
        },
        {
            "lot_id": "L20260430-0003",
            "lot_status": "created",
            "raw_material_id": "RM-SPHC-001",
            "raw_material_name": "SPHC 열연 강판",
            "quantity": 1000.0,
            "unit": "kg",
            "customer_name": "현대자동차(주)",
            "product_code": "PROD-HY-003",
            "product_name": "자동차 브라켓 C형",
            "order_number": "ORD-20260430-003",
        },
    ]

    for lot_data in sample_lots:
        result = await session.execute(
            select(Lot).where(Lot.lot_id == lot_data["lot_id"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  [SKIP] LOT 이미 존재: {lot_data['lot_id']}")
            continue

        lot = Lot(
            lot_id=lot_data["lot_id"],
            lot_status=lot_data["lot_status"],
            raw_material_id=lot_data.get("raw_material_id"),
            raw_material_name=lot_data.get("raw_material_name"),
            quantity=lot_data.get("quantity"),
            unit=lot_data.get("unit"),
            customer_name=lot_data.get("customer_name"),
            product_code=lot_data.get("product_code"),
            product_name=lot_data.get("product_name"),
            order_number=lot_data.get("order_number"),
            created_by=created_by_user.id,
        )
        session.add(lot)
        await session.flush()

        # 생성 이력
        history = LotHistory(
            lot_id_fk=lot.id,
            lot_display_id=lot.lot_id,
            step="LOT 생성 (시드 데이터)",
            from_status=None,
            to_status="created",
            actor_id=created_by_user.id,
            actor_name=created_by_user.full_name,
            detail="초기 데이터 시딩",
        )
        session.add(history)
        print(f"  [CREATE] LOT {lot_data['lot_id']} ({lot_data['lot_status']})")


async def main() -> None:
    print("=" * 60)
    print("Onetouch AI+MES 초기 데이터 시딩 시작")
    print(f"DB: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")
    print("=" * 60)

    # 테이블 생성
    print("\n[1] 테이블 생성...")
    await create_tables()

    # 데이터 시딩
    async with AsyncSessionLocal() as session:
        print("\n[2] 사용자 계정 생성...")
        users = await seed_users(session)

        # 첫 번째 production_manager 사용자를 시드 LOT 생성자로 사용
        prod_manager = next(
            (u for u in users if u.role == "production_manager"), users[0]
        )

        print("\n[3] 샘플 LOT 데이터 생성...")
        await seed_sample_lots(session, prod_manager)

        await session.commit()

    print("\n" + "=" * 60)
    print("시딩 완료!")
    print("\n기본 계정 정보:")
    for u in INITIAL_USERS:
        print(f"  {u['role']:25s}  {u['email']:35s}  PW: {u['password']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
