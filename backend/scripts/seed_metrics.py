"""공정실적(ProcessResult) + 품질검사(QualityInspection) 시드 — 대시보드/KPI 숫자 채우기"""
import asyncio
import sys
import uuid
import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.core.db_compat  # noqa: F401

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.work_order import WorkOrder, ProcessResult
from app.models.lot import Lot
from app.models.equipment import Equipment
from app.models.quality import QualityInspection, DefectDetail
from app.models.inbound import RawMaterialReceipt
from app.models.shipment import Shipment
from app.models.order import Order
from app.models.user import User

random.seed(7)
TODAY = date(2026, 5, 5)   # 오늘 (2026-05-05)


def dt(d: date, hour: int = 9, minute: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=timezone.utc)


def days_ago(n: int) -> date:
    return TODAY - timedelta(days=n)


# ── 일별 생산 계획 (input) / 실적 (output) 기준값
# 월~금 적극 생산, 주말 소폭 유지
def daily_plan(d: date) -> float:
    wd = d.weekday()          # 0=월, 6=일
    base = 1200 if wd < 5 else 400
    return round(base * random.uniform(0.9, 1.1), 1)

def daily_output(plan: float, d: date) -> float:
    wd = d.weekday()
    rate = random.uniform(0.82, 0.97) if wd < 5 else random.uniform(0.7, 0.85)
    return round(plan * rate, 1)

def daily_defect(output: float) -> float:
    rate = random.uniform(0.005, 0.035)   # 0.5 ~ 3.5 %
    return round(output * rate, 1)


DEFECT_TYPES = ["치수불량", "표면스크래치", "용접결함", "도장불량", "균열", "변형", "재료이상"]


async def seed_metrics(db: AsyncSession) -> None:
    print("\n===== 생산 실적 / 품질 / KPI 시드 시작 =====\n")

    # ── 기존 데이터 조회 ────────────────────────────────────
    result = await db.execute(select(User).where(User.email == "admin@onetouch.com"))
    admin = result.scalar_one_or_none()
    admin_id = admin.id if admin else None

    wo_rows = (await db.execute(
        select(WorkOrder.id, WorkOrder.lot_id, WorkOrder.equipment_id, WorkOrder.input_qty)
        .order_by(WorkOrder.created_at)
    )).all()
    if not wo_rows:
        print("❌ WorkOrder 데이터 없음. seed_data.py 먼저 실행하세요.")
        return

    lot_ids = [r.lot_id for r in wo_rows]
    eqp_ids = [r.equipment_id for r in wo_rows if r.equipment_id]
    wo_ids = [r.id for r in wo_rows]

    # ── 기존 ProcessResult 삭제 후 재삽입 (깔끔하게) ──────
    await db.execute(text("DELETE FROM process_results"))
    await db.flush()
    print("   기존 process_results 삭제 완료")

    # ── 기존 QualityInspection / DefectDetail 삭제 후 재삽입
    await db.execute(text("DELETE FROM defect_details"))
    await db.execute(text("DELETE FROM quality_inspections"))
    await db.flush()
    print("   기존 quality_inspections 삭제 완료")

    # ══════════════════════════════════════════════════════
    # 1. ProcessResult — 최근 30일 (일 3~8건, 교대별 실적)
    # ══════════════════════════════════════════════════════
    print("\n1. ProcessResult (공정 실적) 삽입 중...")
    total_pr = 0
    SHIFTS = [         # (시작 시, 종료 시)
        (7, 15), (8, 16), (9, 17), (13, 21), (14, 22), (22, 6),
    ]
    pr_summary: list[dict] = []   # 날짜별 집계용 (대시보드 검증용)

    for day_offset in range(30, -1, -1):   # 30일 전 ~ 오늘
        d = days_ago(day_offset)
        plan_total = daily_plan(d)
        out_total = daily_output(plan_total, d)
        def_total = daily_defect(out_total)

        # 교대별로 쪼개서 여러 건 삽입 (3~6건/일)
        n_shifts = random.randint(3, 6)
        shift_out_list = []
        shift_def_list = []
        remainder_out = out_total
        remainder_def = def_total

        for j in range(n_shifts - 1):
            frac = random.uniform(0.1, 0.3)
            so = round(remainder_out * frac, 1)
            sd = round(remainder_def * frac, 1)
            shift_out_list.append(so)
            shift_def_list.append(sd)
            remainder_out = round(remainder_out - so, 1)
            remainder_def = round(remainder_def - sd, 1)
        shift_out_list.append(max(remainder_out, 0))
        shift_def_list.append(max(remainder_def, 0))

        day_pr = 0
        for j in range(n_shifts):
            sh_start, sh_end = SHIFTS[j % len(SHIFTS)]
            start_dt = dt(d, sh_start, random.randint(0, 15))
            end_dt = dt(d, sh_end, random.randint(0, 30))
            if end_dt <= start_dt:
                end_dt = start_dt + timedelta(hours=8)

            wo_idx = (day_offset * n_shifts + j) % len(wo_ids)
            lot_idx = (day_offset * n_shifts + j) % len(lot_ids)
            eqp_idx = j % len(eqp_ids) if eqp_ids else None

            out_qty = max(shift_out_list[j], 0.1)
            def_qty = min(shift_def_list[j], out_qty * 0.1)   # 최대 10%
            in_qty = round(out_qty + def_qty + random.uniform(0, 20), 1)

            pr = ProcessResult(
                work_order_id=wo_ids[wo_idx],
                lot_id=lot_ids[lot_idx],
                equipment_id=eqp_ids[eqp_idx] if eqp_ids and eqp_idx is not None else None,
                worker_id=admin_id,
                input_qty=in_qty,
                output_qty=out_qty,
                defect_qty=def_qty,
                start_time=start_dt,
                end_time=end_dt,
                created_at=start_dt,
                condition_notes=f"{d.strftime('%Y-%m-%d')} {j+1}교대 실적",
            )
            db.add(pr)
            day_pr += 1

        total_pr += day_pr
        pr_summary.append({
            "date": d.isoformat(),
            "records": day_pr,
            "output": round(out_total, 1),
            "defect": round(def_total, 1),
        })

    await db.flush()
    print(f"   ProcessResult {total_pr}건 삽입 완료")

    # 최근 7일 요약 출력
    print("\n   [최근 7일 생산 실적]")
    print(f"   {'날짜':<12} {'건수':>4} {'생산량':>8} {'불량량':>8}")
    for row in pr_summary[-7:]:
        print(f"   {row['date']:<12} {row['records']:>4} {row['output']:>8.1f} {row['defect']:>8.1f}")

    # ══════════════════════════════════════════════════════
    # 2. QualityInspection — 최근 30일 (일 1~3건)
    # ══════════════════════════════════════════════════════
    print("\n2. QualityInspection (품질 검사) 삽입 중...")
    qi_count = 0
    dd_count = 0
    INSP_TYPES = ["incoming", "in_process", "final"]

    for day_offset in range(30, -1, -1):
        d = days_ago(day_offset)
        n_insp = random.randint(1, 3)

        for j in range(n_insp):
            lot_idx = (day_offset * 3 + j) % len(lot_ids)
            insp_hour = random.randint(9, 17)
            insp_dt = dt(d, insp_hour, random.randint(0, 59))

            # 불량률: 평일 1~3%, 주말 약간 높음
            wd = d.weekday()
            defect_rate = round(random.uniform(0.8, 3.2) if wd < 5 else random.uniform(1.5, 5.0), 2)
            result_str = "pass" if defect_rate < 3.0 else ("conditional_pass" if defect_rate < 4.5 else "fail")

            qi = QualityInspection(
                lot_id=lot_ids[lot_idx],
                inspector_id=admin_id,
                inspection_type=INSP_TYPES[j % len(INSP_TYPES)],
                result=result_str,
                defect_rate=defect_rate,
                inspection_date=insp_dt,
                notes=f"{d.strftime('%Y-%m-%d')} 품질 검사 — {INSP_TYPES[j % len(INSP_TYPES)]}",
                created_at=insp_dt,
            )
            db.add(qi)
            await db.flush()
            qi_count += 1

            if result_str != "pass":
                dtype = random.choice(DEFECT_TYPES)
                dd = DefectDetail(
                    inspection_id=qi.id,
                    defect_code=f"DF-{qi_count:04d}",
                    defect_type=dtype,
                    qty=float(random.randint(1, 20)),
                    description=f"{dtype} 검출 - {d.strftime('%Y-%m-%d')} {INSP_TYPES[j % len(INSP_TYPES)]} 검사",
                )
                db.add(dd)
                dd_count += 1

    await db.flush()
    print(f"   QualityInspection {qi_count}건, DefectDetail {dd_count}건 삽입 완료")

    # ══════════════════════════════════════════════════════
    # 3. 입고 이력 — 오늘 포함 최근 30일 추가 (각 일 1~2건)
    # ══════════════════════════════════════════════════════
    print("\n3. 입고 이력 최근 30일 추가 삽입 중...")
    sup_rows = (await db.execute(
        text("SELECT id, supplier_code FROM suppliers LIMIT 20")
    )).all()
    sup_id_list = [r[0] for r in sup_rows]

    existing_rnums = set((await db.execute(
        text("SELECT receipt_number FROM raw_material_receipts")
    )).scalars().all())

    MAT_NAMES = [
        "SS400 열연강판 3.2T", "SUS304 냉연판 1.5T", "AL5052 알루미늄 2.0T",
        "SM45C 환봉 Φ50", "SS400 각관 50×50×3.2", "SUS316L 판재 2.0T",
        "AL6061 알루미늄 3.0T", "동판 1.0T", "SCM440 합금강봉 Φ60",
        "SS400 열연강판 6.0T",
    ]
    inbound_count = 0
    lot_row_ids = (await db.execute(text("SELECT id FROM lots ORDER BY created_at"))).scalars().all()

    for day_offset in range(30, -1, -1):
        d = days_ago(day_offset)
        n_recv = random.randint(1, 2)
        for k in range(n_recv):
            seq = (30 - day_offset) * 2 + k + 21   # 기존 0020번 이후
            rnum = f"RCV-2026-{seq:04d}"
            if rnum in existing_rnums:
                continue
            existing_rnums.add(rnum)
            mat_idx = (day_offset + k) % len(MAT_NAMES)
            sup_idx = (day_offset + k) % len(sup_id_list)
            lot_idx = (day_offset + k) % len(lot_row_ids) if lot_row_ids else None
            qty = Decimal(str(round(random.uniform(300, 4000), 1)))
            price = Decimal(str(random.randint(800, 6000)))
            db.add(RawMaterialReceipt(
                receipt_number=rnum,
                supplier_id=uuid.UUID(bytes=bytes.fromhex(str(sup_id_list[sup_idx]).replace("-",""))),
                lot_id=uuid.UUID(bytes=bytes.fromhex(str(lot_row_ids[lot_idx]).replace("-",""))) if lot_idx is not None else None,
                material_name=MAT_NAMES[mat_idx],
                material_code=f"MAT-{(mat_idx+1):03d}",
                quantity=qty,
                unit="kg",
                unit_price=price,
                received_date=d,
                notes=f"{d.strftime('%Y-%m-%d')} 정기 입고",
                created_by=admin_id,
            ))
            inbound_count += 1

    await db.flush()
    print(f"   입고 이력 {inbound_count}건 추가 완료")

    # ══════════════════════════════════════════════════════
    # 4. 출하 — 오늘 포함 최근 30일 추가
    # ══════════════════════════════════════════════════════
    print("\n4. 출하 최근 30일 추가 삽입 중...")
    cust_rows = (await db.execute(
        text("SELECT id FROM customers LIMIT 20")
    )).scalars().all()

    existing_snums = set((await db.execute(
        text("SELECT shipment_number FROM shipments")
    )).scalars().all())

    from app.models.shipment import ShipmentLot
    SHIP_STATUS_BY_AGE = {
        range(0, 3): "pending",
        range(3, 10): "shipped",
        range(10, 31): "delivered",
    }
    ship_count = 0
    for day_offset in range(30, -1, -1):
        d = days_ago(day_offset)
        n_ship = random.randint(1, 2)
        for k in range(n_ship):
            seq = (30 - day_offset) * 2 + k + 21
            snum = f"SHP-2026-{seq:04d}"
            if snum in existing_snums:
                continue
            existing_snums.add(snum)

            status = "pending"
            for age_range, s in SHIP_STATUS_BY_AGE.items():
                if day_offset in age_range:
                    status = s
                    break

            cust_idx = (day_offset + k) % len(cust_rows)
            shipped_dt = dt(d, 10) if status in ("shipped", "delivered") else None
            delivered_dt = dt(d + timedelta(days=random.randint(1, 3)), 14) if status == "delivered" else None

            shipment = Shipment(
                shipment_number=snum,
                customer_id=uuid.UUID(bytes=bytes.fromhex(str(cust_rows[cust_idx]).replace("-",""))),
                status=status,
                planned_date=d,
                shipped_date=shipped_dt,
                delivered_date=delivered_dt,
                notes=f"{d.strftime('%Y-%m-%d')} 출하",
                created_by=admin_id,
            )
            db.add(shipment)
            await db.flush()

            lot_idx = (day_offset + k) % len(lot_row_ids)
            db.add(ShipmentLot(
                shipment_id=shipment.id,
                lot_id=uuid.UUID(bytes=bytes.fromhex(str(lot_row_ids[lot_idx]).replace("-",""))),
                qty=round(random.uniform(100, 2000), 1),
                unit_price=round(random.uniform(50000, 800000), 0),
            ))
            ship_count += 1

    await db.flush()
    print(f"   출하 {ship_count}건 추가 완료")

    # ══════════════════════════════════════════════════════
    # 5. 수주 납기 준수 데이터 — completed Orders의 updated_at 업데이트
    # ══════════════════════════════════════════════════════
    print("\n5. 수주 납기 준수율 데이터 보정 중...")
    completed_orders = (await db.execute(
        select(Order).where(Order.status == "completed")
    )).scalars().all()
    for order in completed_orders:
        # due_date 이내에 완료된 것으로 updated_at 보정
        if order.due_date:
            complete_date = order.due_date - timedelta(days=random.randint(0, 5))
            order.updated_at = dt(complete_date, 16)
    await db.flush()
    print(f"   수주 {len(completed_orders)}건 납기 준수 데이터 보정 완료")

    await db.commit()
    print("\n===== 시드 완료 =====\n")


async def main():
    async with AsyncSessionLocal() as db:
        await seed_metrics(db)


if __name__ == "__main__":
    asyncio.run(main())
