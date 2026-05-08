"""추가 시드 데이터 — 출하물류 10개 / 입고 10개 / 수주 10개 / 견적 10개"""
import asyncio
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.core.db_compat  # noqa: F401

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal as AsyncSessionFactory
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.lot import Lot
from app.models.inbound import RawMaterialReceipt
from app.models.order import Order, OrderItem
from app.models.shipment import Shipment, ShipmentLot
from app.models.quotation import Quotation, QuotationItem
from app.models.user import User

random.seed(99)
today = date(2026, 5, 5)
now_utc = datetime.now(timezone.utc)


def days_ago(n: int) -> date:
    return today - timedelta(days=n)


def dt_ago(days: int, hours: int = 0) -> datetime:
    return now_utc - timedelta(days=days, hours=hours)


PRODUCT_NAMES = [
    "자동차 도어 브라켓", "엔진 마운팅 브래킷", "배터리 케이스 커버", "전장 하우징 패널",
    "구조용 프레임 조립체", "압력 용기 플랜지", "열교환기 튜브시트", "용접 구조물 프레임",
    "펌프 케이싱 부품", "밸브 바디 가공품",
]

MATERIAL_PAIRS = [
    ("MAT-001", "SS400 열연강판 3.2T",  "kg",  8_500),
    ("MAT-002", "SS400 열연강판 6.0T",  "kg",  6_200),
    ("MAT-003", "SS400 열연강판 9.0T",  "kg",  4_800),
    ("MAT-004", "SUS304 냉연판 1.5T",   "kg",  4_500),
    ("MAT-005", "SUS304 냉연판 3.0T",   "kg",  4_300),
    ("MAT-006", "SUS316L 판재 2.0T",    "kg",  5_800),
    ("MAT-007", "AL5052 알루미늄 2.0T", "kg",  3_200),
    ("MAT-008", "AL6061 알루미늄 3.0T", "kg",  3_600),
    ("MAT-009", "AL6063 압출재",         "m",   2_800),
    ("MAT-010", "동판 1.0T",             "kg", 12_000),
]


async def seed(db: AsyncSession) -> None:
    print("\n===== 추가 시드 데이터 삽입 시작 =====\n")

    # ── 기준 데이터 로드 ────────────────────────────
    admin = (await db.execute(
        select(User).where(User.email == "admin@onetouch.com")
    )).scalar_one_or_none()
    admin_id = admin.id if admin else None

    customers = (await db.execute(select(Customer).where(Customer.is_active == True)  # noqa: E712
                                  .limit(20))).scalars().all()
    suppliers = (await db.execute(select(Supplier).where(Supplier.is_active == True)  # noqa: E712
                                  .limit(20))).scalars().all()
    lots      = (await db.execute(select(Lot).limit(20))).scalars().all()

    if not customers:
        print("ERROR: 고객사가 없습니다. seed_data.py를 먼저 실행하세요.")
        return
    if not suppliers:
        print("ERROR: 공급업체가 없습니다. seed_data.py를 먼저 실행하세요.")
        return
    if not lots:
        print("ERROR: LOT이 없습니다. seed_data.py를 먼저 실행하세요.")
        return

    print(f"   기준 데이터: 고객 {len(customers)}개, 공급업체 {len(suppliers)}개, LOT {len(lots)}개")

    # ── 1. 입고 10개 (RCV-2026-021 ~ 030) ──────────
    print("1. 원자재 입고 10개 삽입...")
    existing_rcv = set((await db.execute(select(RawMaterialReceipt.receipt_number))).scalars().all())
    added_rcv = 0
    for i in range(10):
        rnum = f"RCV-2026-{21 + i:04d}"
        if rnum in existing_rcv:
            continue
        mat_code, mat_name, unit, unit_price = MATERIAL_PAIRS[i % len(MATERIAL_PAIRS)]
        sup = suppliers[i % len(suppliers)]
        qty = round(random.uniform(300, 5000), 1)
        receipt = RawMaterialReceipt(
            receipt_number=rnum,
            supplier_id=sup.id,
            lot_id=lots[i % len(lots)].id if lots else None,
            material_name=mat_name,
            material_code=mat_code,
            quantity=Decimal(str(qty)),
            unit=unit,
            unit_price=Decimal(str(unit_price)),
            received_date=days_ago(30 - i * 3),
            notes=f"{sup.name} — {mat_name} 정기 납품 {i + 1}차",
            created_by=admin_id,
        )
        db.add(receipt)
        added_rcv += 1
    await db.flush()
    print(f"   입고 완료 ({added_rcv}개 추가)")

    # ── 2. 수주 10개 (ORD-2026-021 ~ 030) ──────────
    print("2. 수주 10개 삽입...")
    existing_orders = set((await db.execute(select(Order.order_number))).scalars().all())
    ORDER_STATUSES = [
        "received", "confirmed", "in_production", "shipped", "completed",
        "confirmed", "received", "in_production", "completed", "shipped",
    ]
    order_ids: list[uuid.UUID] = []
    added_ord = 0
    for i in range(10):
        onum = f"ORD-2026-{21 + i:04d}"
        if onum in existing_orders:
            r = await db.execute(select(Order).where(Order.order_number == onum))
            order_ids.append(r.scalar_one().id)
            continue
        cust = customers[i % len(customers)]
        ordered = days_ago(28 - i * 2)
        due = ordered + timedelta(days=random.randint(14, 45))
        qty = Decimal(str(round(random.uniform(50, 500))))
        price = Decimal(str(round(random.uniform(500_000, 8_000_000))))
        order = Order(
            order_number=onum,
            customer_id=cust.id,
            status=ORDER_STATUSES[i],
            ordered_date=ordered,
            due_date=due,
            total_amount=price * qty,
            notes=f"{PRODUCT_NAMES[i]} 추가 발주 ({i + 1}차)",
            created_by=admin_id,
        )
        db.add(order)
        await db.flush()
        order_ids.append(order.id)

        mat_code, mat_name, unit, unit_price = MATERIAL_PAIRS[i % len(MATERIAL_PAIRS)]
        item = OrderItem(
            order_id=order.id,
            material_code=mat_code,
            material_name=mat_name,
            quantity=qty,
            unit="개",
            unit_price=price,
        )
        db.add(item)
        added_ord += 1
    await db.flush()
    print(f"   수주 완료 ({added_ord}개 추가)")

    # ── 3. 견적 10개 (QUO-2026-001 ~ 010) ──────────
    print("3. 견적 10개 삽입...")
    existing_quo = set((await db.execute(select(Quotation.quotation_number))).scalars().all())
    QUO_STATUSES = [
        "accepted", "accepted", "submitted", "submitted", "draft",
        "accepted", "rejected", "submitted", "draft", "accepted",
    ]
    PROCESS_TYPES = [
        ("레이저 절단",   "cutting"),
        ("CNC 절삭",     "cutting"),
        ("MIG 용접",     "welding"),
        ("분체 도장",    "painting"),
        ("외관 검사",    "inspection"),
    ]
    added_quo = 0
    for i in range(10):
        qnum = f"QUO-2026-{i + 1:04d}"
        if qnum in existing_quo:
            continue
        cust = customers[i % len(customers)]
        mat_cost  = Decimal(str(round(random.uniform(200_000, 3_000_000))))
        proc_cost = Decimal(str(round(random.uniform(100_000, 1_500_000))))
        total     = mat_cost + proc_cost
        margin    = Decimal("0.15")
        final     = (total * (1 + margin)).quantize(Decimal("1"))
        status    = QUO_STATUSES[i]
        valid_days = 30 if status in ("draft", "submitted") else 60
        order_ref = order_ids[i] if i < len(order_ids) and status == "accepted" else None

        quo = Quotation(
            quotation_number=qnum,
            customer_id=cust.id,
            order_id=order_ref,
            status=status,
            material_cost=mat_cost,
            process_cost=proc_cost,
            total_amount=total,
            margin_rate=margin,
            final_amount=final,
            valid_until=days_ago(-valid_days),  # 미래 만료일
            notes=f"{PRODUCT_NAMES[i]} — AI 자동 견적 ({i + 1}차)",
            version=1,
            created_by=admin_id,
        )
        db.add(quo)
        await db.flush()

        # 견적 항목 2개 (재료비 + 공정비)
        mat_code, mat_name, unit, _ = MATERIAL_PAIRS[i % len(MATERIAL_PAIRS)]
        mat_qty = Decimal(str(round(random.uniform(100, 2000), 1)))
        db.add(QuotationItem(
            quotation_id=quo.id,
            item_type="material",
            description=f"{mat_name} ({mat_code})",
            quantity=mat_qty,
            unit=unit,
            unit_price=(mat_cost / mat_qty).quantize(Decimal("0.01")),
            amount=mat_cost,
            sort_order=1,
        ))

        proc_name, _ = PROCESS_TYPES[i % len(PROCESS_TYPES)]
        proc_hrs = Decimal(str(round(random.uniform(2, 20), 1)))
        db.add(QuotationItem(
            quotation_id=quo.id,
            item_type="process",
            description=f"{proc_name} 가공비",
            quantity=proc_hrs,
            unit="hr",
            unit_price=(proc_cost / proc_hrs).quantize(Decimal("0.01")),
            amount=proc_cost,
            sort_order=2,
        ))
        added_quo += 1
    await db.flush()
    print(f"   견적 완료 ({added_quo}개 추가)")

    # ── 4. 출하 10개 (SHP-2026-021 ~ 030) ──────────
    print("4. 출하 10개 삽입...")
    existing_ship = set((await db.execute(select(Shipment.shipment_number))).scalars().all())
    # 이미 shipment_lots에 연결된 lot_id 목록 조회 (중복 방지)
    used_lot_ids = set((await db.execute(select(ShipmentLot.lot_id))).scalars().all())
    available_lots = [lot for lot in lots if lot.id not in used_lot_ids]

    SHIP_STATUSES = [
        "delivered", "delivered", "shipped", "shipped", "pending",
        "delivered", "shipped", "pending", "delivered", "shipped",
    ]
    added_ship = 0
    lot_cursor = 0
    for i in range(10):
        snum = f"SHP-2026-{21 + i:04d}"
        if snum in existing_ship:
            continue
        cust = customers[i % len(customers)]
        planned = days_ago(20 - i * 2)
        ship_status = SHIP_STATUSES[i]
        shipped_dt  = dt_ago(18 - i * 2) if ship_status in ("shipped", "delivered") else None
        delivered_dt = dt_ago(15 - i * 2) if ship_status == "delivered" else None

        shipment = Shipment(
            shipment_number=snum,
            customer_id=cust.id,
            status=ship_status,
            planned_date=planned,
            shipped_date=shipped_dt,
            delivered_date=delivered_dt,
            notes=f"{cust.name} 추가 출하 {i + 1}차",
            created_by=admin_id,
        )
        db.add(shipment)
        await db.flush()

        # 사용 가능한 lot이 있으면 연결, 없으면 건너뜀
        if lot_cursor < len(available_lots):
            sl = ShipmentLot(
                shipment_id=shipment.id,
                lot_id=available_lots[lot_cursor].id,
                qty=round(random.uniform(50, 2000), 1),
                unit_price=round(random.uniform(50_000, 800_000)),
            )
            db.add(sl)
            lot_cursor += 1
        added_ship += 1
    await db.flush()
    print(f"   출하 완료 ({added_ship}개 추가)")

    await db.commit()
    print("\n===== 추가 시드 데이터 삽입 완료 =====\n")
    print("요약:")
    print(f"  입고(RCV):  {added_rcv}개 추가")
    print(f"  수주(ORD):  {added_ord}개 추가")
    print(f"  견적(QUO):  {added_quo}개 추가")
    print(f"  출하(SHP):  {added_ship}개 추가")


async def main():
    async with AsyncSessionFactory() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
