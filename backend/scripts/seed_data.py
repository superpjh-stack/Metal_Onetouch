"""시드 데이터 삽입 스크립트 — 테이블별 20개씩"""
import asyncio
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.core.db_compat  # noqa: F401 — JSONB/TIMESTAMPTZ 패치

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal as AsyncSessionFactory
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.raw_material import RawMaterial
from app.models.process_type import ProcessType
from app.models.equipment import Equipment
from app.models.lot import Lot, LotHistory
from app.models.inbound import RawMaterialReceipt
from app.models.order import Order, OrderItem
from app.models.work_order import WorkOrder
from app.models.quality import QualityInspection, DefectDetail
from app.models.shipment import Shipment, ShipmentLot
from app.models.kpi import KpiTarget
from app.models.user import User

random.seed(42)
today = date(2026, 5, 4)
now_utc = datetime.now(timezone.utc)


def days_ago(n: int) -> date:
    return today - timedelta(days=n)


def dt_ago(days: int, hours: int = 0) -> datetime:
    return now_utc - timedelta(days=days, hours=hours)


# ─────────────────────────────────────────────
# 1. 고객사 20개
# ─────────────────────────────────────────────
CUSTOMERS = [
    ("CST-001", "현대모비스㈜",       "김정훈", "031-520-1234", "A급",  500_000_000),
    ("CST-002", "기아자동차㈜",       "이선영", "02-3464-2000", "A급",  800_000_000),
    ("CST-003", "삼성전자㈜",         "박민준", "031-200-1114", "A급", 1_000_000_000),
    ("CST-004", "LG전자㈜",           "최수현", "02-3777-1114", "A급",  600_000_000),
    ("CST-005", "한화에어로스페이스",  "정우성", "055-260-2114", "B급",  300_000_000),
    ("CST-006", "두산에너빌리티㈜",    "강지민", "055-278-0114", "B급",  250_000_000),
    ("CST-007", "포스코홀딩스㈜",     "윤서준", "054-220-0114", "A급",  700_000_000),
    ("CST-008", "현대중공업㈜",       "임채원", "052-202-2114", "A급",  450_000_000),
    ("CST-009", "롯데케미칼㈜",       "한지아", "02-3459-1600", "B급",  200_000_000),
    ("CST-010", "SK하이닉스㈜",       "오준혁", "031-5185-1000","A급",  900_000_000),
    ("CST-011", "코오롱인더㈜",       "신예린", "02-3677-3700", "C급",  100_000_000),
    ("CST-012", "효성중공업㈜",       "권도현", "02-707-7000",  "B급",  180_000_000),
    ("CST-013", "LS일렉트릭㈜",       "배수아", "043-260-6000", "B급",  220_000_000),
    ("CST-014", "현대건설㈜",         "양태준", "02-746-1114",  "B급",  150_000_000),
    ("CST-015", "GS건설㈜",           "서민지", "02-2154-1000", "C급",   80_000_000),
    ("CST-016", "삼성중공업㈜",       "노준서", "055-630-0114", "A급",  380_000_000),
    ("CST-017", "한국전력㈜",         "문하은", "061-345-3114", "A급",  500_000_000),
    ("CST-018", "KT㈜",               "안지후", "02-1588-0016", "B급",  160_000_000),
    ("CST-019", "대우조선해양㈜",     "황세은", "055-680-0114", "B급",  270_000_000),
    ("CST-020", "현대제철㈜",         "류지원", "041-930-0114", "A급",  420_000_000),
]

# ─────────────────────────────────────────────
# 2. 공급업체 20개
# ─────────────────────────────────────────────
SUPPLIERS = [
    ("SUP-001", "현대철강㈜",         "강민우", "054-220-1000", "A"),
    ("SUP-002", "POSCO C&C",          "이지수", "054-220-2000", "A"),
    ("SUP-003", "동국제강㈜",         "박혁진", "02-317-1114",  "A"),
    ("SUP-004", "세아제강㈜",         "최연우", "02-3469-0114", "B"),
    ("SUP-005", "넥스틸㈜",           "정수빈", "054-281-3000", "B"),
    ("SUP-006", "현대BNG스틸",        "김도윤", "041-930-2000", "A"),
    ("SUP-007", "아주스틸㈜",         "나은채", "031-371-0200", "B"),
    ("SUP-008", "KG스틸㈜",           "백준혁", "062-600-2000", "B"),
    ("SUP-009", "포스코스틸리온",     "유지민", "054-220-3000", "A"),
    ("SUP-010", "한국스틸㈜",         "엄현서", "055-320-1000", "C"),
    ("SUP-011", "알코아코리아",       "추성우", "032-580-3000", "A"),
    ("SUP-012", "노벨리스코리아",     "탁소연", "032-580-4000", "A"),
    ("SUP-013", "삼화알루미늄",       "허다은", "031-499-0114", "B"),
    ("SUP-014", "코리아알루미늄",     "마준수", "032-580-5000", "C"),
    ("SUP-015", "LS니꼬동제련",       "방지율", "02-2189-8114", "A"),
    ("SUP-016", "고려아연㈜",         "사민준", "055-240-0114", "A"),
    ("SUP-017", "풍산㈜",             "아서윤", "054-530-0114", "B"),
    ("SUP-018", "대한특수강",         "자예원", "032-580-6000", "C"),
    ("SUP-019", "삼현철강",           "차우진", "051-600-1000", "C"),
    ("SUP-020", "한국특수형강",       "카지윤", "031-499-0200", "B"),
]

# ─────────────────────────────────────────────
# 3. 공정 마스터 (7가지 표준 + 추가 13 = 20개)
# ─────────────────────────────────────────────
PROCESSES = [
    ("PRC-001", "레이저 절단",       "cutting",    25, "파이버 레이저 절단 공정"),
    ("PRC-002", "플라즈마 절단",     "cutting",    30, "두꺼운 강판 플라즈마 절단"),
    ("PRC-003", "CNC 절삭",          "cutting",    45, "CNC 밀링/터닝 절삭 가공"),
    ("PRC-004", "프레스 성형",       "forming",    20, "유압 프레스 판금 성형"),
    ("PRC-005", "벤딩",              "forming",    15, "CNC 벤딩 머신 절곡"),
    ("PRC-006", "롤 포밍",           "forming",    35, "냉간 롤 포밍 공정"),
    ("PRC-007", "MIG 용접",          "welding",    40, "반자동 MIG 용접"),
    ("PRC-008", "TIG 용접",          "welding",    55, "정밀 TIG 아르곤 용접"),
    ("PRC-009", "로봇 용접",         "welding",    30, "로봇 자동 용접 셀"),
    ("PRC-010", "분체 도장",         "painting",   60, "정전 분체 도장 공정"),
    ("PRC-011", "액체 도장",         "painting",   45, "습식 액체 도장 공정"),
    ("PRC-012", "도금",              "painting",   90, "아연·니켈 도금 처리"),
    ("PRC-013", "외관 검사",         "inspection", 10, "육안 치수 외관 검사"),
    ("PRC-014", "비파괴 검사",       "inspection", 20, "초음파 자분 비파괴 검사"),
    ("PRC-015", "3D 측정",           "inspection", 15, "3D 스캐너 정밀 측정"),
    ("PRC-016", "조립",              "assembly",   50, "부품 조립 및 체결"),
    ("PRC-017", "볼트 체결",         "assembly",   20, "토크 관리 볼트 체결"),
    ("PRC-018", "포장",              "other",      10, "PE 비닐 박스 포장"),
    ("PRC-019", "열처리",            "other",     120, "담금질·뜨임 열처리"),
    ("PRC-020", "쇼트 블라스팅",     "other",      30, "표면 녹 이물질 제거"),
]

# ─────────────────────────────────────────────
# 4. 설비 20개 (공정코드 참조)
# ─────────────────────────────────────────────
EQUIPMENT_DATA = [
    ("EQP-001", "레이저 절단기 #1",   "PRC-001", "TRUMPF",     "TruLaser3030", "running",   "A구역"),
    ("EQP-002", "레이저 절단기 #2",   "PRC-001", "BYSTRONIC",  "ByStar Fiber", "running",   "A구역"),
    ("EQP-003", "플라즈마 절단기 #1", "PRC-002", "HYPERTHERM", "XPR300",       "idle",      "A구역"),
    ("EQP-004", "CNC 머시닝센터 #1",  "PRC-003", "DMG MORI",   "DMC 80H",      "running",   "B구역"),
    ("EQP-005", "CNC 머시닝센터 #2",  "PRC-003", "DOOSAN",     "DNM 6700",     "running",   "B구역"),
    ("EQP-006", "CNC 선반 #1",        "PRC-003", "HWACHEON",   "Hi-TECH 350",  "maintenance","B구역"),
    ("EQP-007", "유압 프레스 #1",     "PRC-004", "KOMATSU",    "H1F-300",      "running",   "C구역"),
    ("EQP-008", "유압 프레스 #2",     "PRC-004", "AIDA",       "SDE-300",      "idle",      "C구역"),
    ("EQP-009", "CNC 벤딩기 #1",      "PRC-005", "AMADA",      "HFE-M2",       "running",   "C구역"),
    ("EQP-010", "CNC 벤딩기 #2",      "PRC-005", "TRUMPF",     "TruBend 5085", "running",   "C구역"),
    ("EQP-011", "MIG 용접기 #1",      "PRC-007", "LINCOLN",    "Power Wave S7","running",   "D구역"),
    ("EQP-012", "MIG 용접기 #2",      "PRC-007", "MILLER",     "XMT 350",      "running",   "D구역"),
    ("EQP-013", "TIG 용접기 #1",      "PRC-008", "FRONIUS",    "TIG 4000",     "idle",      "D구역"),
    ("EQP-014", "로봇 용접 셀 #1",    "PRC-009", "HYUNDAI",    "HX165",        "running",   "D구역"),
    ("EQP-015", "분체 도장 부스 #1",  "PRC-010", "NORDSON",    "Sure Coat",    "running",   "E구역"),
    ("EQP-016", "도장 오븐 #1",       "PRC-011", "ANEST IWATA","WA-120",       "running",   "E구역"),
    ("EQP-017", "도금조 #1",          "PRC-012", "국산",       "ZN-LINE-01",   "idle",      "E구역"),
    ("EQP-018", "3D 측정기 #1",       "PRC-015", "ZEISS",      "Contura G2",   "running",   "F구역"),
    ("EQP-019", "열처리로 #1",        "PRC-019", "AICHELIN",   "HBSE-60",      "running",   "G구역"),
    ("EQP-020", "쇼트 블라스팅기 #1", "PRC-020", "WHEELABRATOR","4-ECA",       "running",   "G구역"),
]

# ─────────────────────────────────────────────
# 5. 원자재 20개
# ─────────────────────────────────────────────
MATERIALS = [
    ("MAT-001", "SS400 열연강판 3.2T",  "steel_sheet", "SS400, 3.2×1219×2438mm", "kg",  "SUP-001", 8500,  500,  1200),
    ("MAT-002", "SS400 열연강판 6.0T",  "steel_sheet", "SS400, 6.0×1219×2438mm", "kg",  "SUP-001", 6200,  300,  1100),
    ("MAT-003", "SS400 열연강판 9.0T",  "steel_sheet", "SS400, 9.0×1219×2438mm", "kg",  "SUP-002", 4800,  200,  1050),
    ("MAT-004", "SUS304 냉연판 1.5T",   "stainless",   "SUS304, 1.5×1219×2438mm","kg",  "SUP-003", 3200,  150,  4500),
    ("MAT-005", "SUS304 냉연판 3.0T",   "stainless",   "SUS304, 3.0×1219×2438mm","kg",  "SUP-003", 2900,  100,  4300),
    ("MAT-006", "SUS316L 판재 2.0T",    "stainless",   "SUS316L, 2.0×1219×2438mm","kg", "SUP-004", 1800,   80,  5800),
    ("MAT-007", "AL5052 알루미늄 2.0T", "aluminum",    "AL5052-H32, 2.0×1219×2438mm","kg","SUP-011",2400, 120,  3200),
    ("MAT-008", "AL6061 알루미늄 3.0T", "aluminum",    "AL6061-T6, 3.0×1219×2438mm","kg","SUP-011", 1900,  90,  3600),
    ("MAT-009", "AL6063 압출재",         "aluminum",    "AL6063-T5, 50×50mm 각재", "m",   "SUP-012", 800,   50,  2800),
    ("MAT-010", "동판 1.0T",             "copper",      "C1100P-1/2H, 1.0×1000×2000mm","kg","SUP-015",600, 30, 12000),
    ("MAT-011", "KS D3507 배관용강관 2인치","pipe",     "SGP 2\" SCH40",           "m",   "SUP-005", 1200,  80,  2100),
    ("MAT-012", "KS D3507 배관용강관 4인치","pipe",     "SGP 4\" SCH40",           "m",   "SUP-005", 800,   50,  2800),
    ("MAT-013", "SM45C 환봉 Φ50",       "bar",         "SM45C, Φ50×6000mm",       "개",  "SUP-018", 350,   30,  8500),
    ("MAT-014", "SM45C 환봉 Φ100",      "bar",         "SM45C, Φ100×6000mm",      "개",  "SUP-018", 180,   20, 14000),
    ("MAT-015", "SCM440 합금강봉 Φ60",  "bar",         "SCM440, Φ60×6000mm",      "개",  "SUP-018", 120,   15, 18000),
    ("MAT-016", "SS400 각관 50×50×3.2", "steel_sheet", "SS400 각관 50×50×3.2T",   "m",   "SUP-007", 1500, 100,  1800),
    ("MAT-017", "SS400 H빔 150×75",      "steel_sheet", "SS400 H형강 150×75×5×7",  "m",   "SUP-006", 600,   40,  3200),
    ("MAT-018", "SUS304 환봉 Φ30",      "stainless",   "SUS304, Φ30×6000mm",      "개",  "SUP-003", 420,   30,  7200),
    ("MAT-019", "황동봉 C3604 Φ20",     "other",       "C3604BD Φ20×3000mm",      "개",  "SUP-016", 280,   20,  9800),
    ("MAT-020", "크롬강봉 SCr420 Φ40",  "other",       "SCr420H Φ40×6000mm",      "개",  "SUP-019", 160,   15, 11000),
]

# ─────────────────────────────────────────────
# LOT 상태 및 고객 이름 목록
# ─────────────────────────────────────────────
LOT_STATUSES = [
    "received", "in_process", "in_process", "in_inspection",
    "completed", "shipped", "received", "in_process",
    "in_inspection", "completed", "shipped", "received",
    "in_process", "on_hold", "completed", "in_process",
    "in_inspection", "completed", "shipped", "delivered",
]

CUSTOMER_NAMES = [c[1] for c in CUSTOMERS]
MATERIAL_NAMES = [m[1] for m in MATERIALS]
PRODUCT_NAMES = [
    "자동차 도어 브라켓", "엔진 마운팅 브래킷", "배터리 케이스 커버", "전장 하우징 패널",
    "구조용 프레임 조립체", "압력 용기 플랜지", "열교환기 튜브시트", "용접 구조물 프레임",
    "펌프 케이싱 부품", "밸브 바디 가공품", "컨베이어 롤러 샤프트", "기어박스 하우징",
    "유압 실린더 로드", "정밀 블록 가공품", "알루미늄 방열 하우징", "스테인리스 탱크",
    "파이프 매니폴드", "CNC 정밀 부품", "로봇 아암 링크", "레이저 커팅 판넬",
]


async def seed(db: AsyncSession) -> None:
    print("\n===== 시드 데이터 삽입 시작 =====\n")

    # ── 어드민 사용자 ID 조회 ──────────────────────
    result = await db.execute(select(User).where(User.email == "admin@onetouch.com"))
    admin = result.scalar_one_or_none()
    admin_id = admin.id if admin else None
    print(f"Admin ID: {admin_id}")

    # ── 1. 고객사 ──────────────────────────────────
    print("1. 고객사 20개 삽입...")
    customer_ids: dict[str, uuid.UUID] = {}
    existing = (await db.execute(select(Customer.customer_code))).scalars().all()
    for code, name, contact, phone, grade, limit in CUSTOMERS:
        if code in existing:
            r = await db.execute(select(Customer).where(Customer.customer_code == code))
            customer_ids[code] = r.scalar_one().id
            continue
        c = Customer(
            customer_code=code, name=name, contact_person=contact,
            phone=phone, credit_limit=Decimal(str(limit)), is_active=True,
        )
        db.add(c)
        await db.flush()
        customer_ids[code] = c.id
    print(f"   고객사 완료 ({len(customer_ids)}개)")

    # ── 2. 공급업체 ─────────────────────────────────
    print("2. 공급업체 20개 삽입...")
    supplier_ids: dict[str, uuid.UUID] = {}
    existing = (await db.execute(select(Supplier.supplier_code))).scalars().all()
    for code, name, contact, phone, grade in SUPPLIERS:
        if code in existing:
            r = await db.execute(select(Supplier).where(Supplier.supplier_code == code))
            supplier_ids[code] = r.scalar_one().id
            continue
        s = Supplier(
            supplier_code=code, name=name, contact_person=contact,
            phone=phone, grade=grade, is_active=True,
        )
        db.add(s)
        await db.flush()
        supplier_ids[code] = s.id
    print(f"   공급업체 완료 ({len(supplier_ids)}개)")

    # ── 3. 공정 마스터 ──────────────────────────────
    print("3. 공정 마스터 20개 삽입...")
    process_ids: dict[str, uuid.UUID] = {}
    existing = (await db.execute(select(ProcessType.process_code))).scalars().all()
    for code, name, ptype, std_time, desc in PROCESSES:
        if code in existing:
            r = await db.execute(select(ProcessType).where(ProcessType.process_code == code))
            process_ids[code] = r.scalar_one().id
            continue
        p = ProcessType(
            process_code=code, name=name, process_type=ptype,
            std_time_min=std_time, description=desc, is_active=True,
        )
        db.add(p)
        await db.flush()
        process_ids[code] = p.id
    print(f"   공정 마스터 완료 ({len(process_ids)}개)")

    # ── 4. 설비 ─────────────────────────────────────
    print("4. 설비 20개 삽입...")
    equipment_ids: dict[str, uuid.UUID] = {}
    existing = (await db.execute(select(Equipment.equipment_code))).scalars().all()
    for code, name, prc_code, mfr, model_no, status, loc in EQUIPMENT_DATA:
        if code in existing:
            r = await db.execute(select(Equipment).where(Equipment.equipment_code == code))
            equipment_ids[code] = r.scalar_one().id
            continue
        e = Equipment(
            equipment_code=code, name=name,
            process_id=process_ids.get(prc_code),
            manufacturer=mfr, model_no=model_no,
            status=status, location=loc,
            installed_at=days_ago(random.randint(365, 1800)),
            last_maint_at=days_ago(random.randint(7, 90)),
            is_active=True,
        )
        db.add(e)
        await db.flush()
        equipment_ids[code] = e.id
    print(f"   설비 완료 ({len(equipment_ids)}개)")

    # ── 5. 원자재 마스터 ────────────────────────────
    print("5. 원자재 마스터 20개 삽입...")
    material_ids: dict[str, uuid.UUID] = {}
    existing = (await db.execute(select(RawMaterial.material_code))).scalars().all()
    for code, name, cat, spec, unit, sup_code, stock, min_stock, price in MATERIALS:
        if code in existing:
            r = await db.execute(select(RawMaterial).where(RawMaterial.material_code == code))
            material_ids[code] = r.scalar_one().id
            continue
        m = RawMaterial(
            material_code=code, name=name, category=cat, spec=spec,
            unit=unit, supplier_id=supplier_ids.get(sup_code),
            stock_qty=Decimal(str(stock)), min_stock_qty=Decimal(str(min_stock)),
            unit_price=Decimal(str(price)), lead_time_days=random.randint(3, 14),
            is_active=True,
        )
        db.add(m)
        await db.flush()
        material_ids[code] = m.id
    print(f"   원자재 마스터 완료 ({len(material_ids)}개)")

    # ── 6. LOT 20개 ─────────────────────────────────
    print("6. LOT 20개 삽입...")
    lot_ids: list[uuid.UUID] = []
    lot_display_ids: list[str] = []
    existing_lots = (await db.execute(select(Lot.lot_id))).scalars().all()

    mat_codes = list(material_ids.keys())
    sup_codes = list(supplier_ids.keys())
    cust_names_list = CUSTOMER_NAMES

    for i in range(20):
        lot_date = days_ago(20 - i)
        lot_display = f"L{lot_date.strftime('%Y%m%d')}-{(i+1):04d}"
        if lot_display in existing_lots:
            r = await db.execute(select(Lot).where(Lot.lot_id == lot_display))
            lot = r.scalar_one()
            lot_ids.append(lot.id)
            lot_display_ids.append(lot_display)
            continue

        mat_code = mat_codes[i % len(mat_codes)]
        mat_name = MATERIAL_NAMES[i % len(MATERIAL_NAMES)]
        status = LOT_STATUSES[i]
        lot = Lot(
            lot_id=lot_display,
            lot_status=status,
            raw_material_id=mat_code,
            raw_material_name=mat_name,
            quantity=round(random.uniform(100, 5000), 1),
            unit="kg",
            customer_name=cust_names_list[i % len(cust_names_list)],
            product_code=f"PRD-{(i+1):04d}",
            product_name=PRODUCT_NAMES[i],
            order_number=f"ORD-2026-{(i+1):04d}",
            planned_start_date=lot_date,
            planned_end_date=lot_date + timedelta(days=random.randint(3, 14)),
            actual_start_date=lot_date if status not in ("created",) else None,
            actual_end_date=lot_date + timedelta(days=random.randint(5, 20)) if status in ("completed", "shipped", "delivered") else None,
            created_by=admin_id,
        )
        db.add(lot)
        await db.flush()
        lot_ids.append(lot.id)
        lot_display_ids.append(lot_display)

        # LOT 이력 1건
        history = LotHistory(
            lot_id_fk=lot.id,
            lot_display_id=lot_display,
            step="입고 등록",
            from_status=None,
            to_status=status,
            actor_id=admin_id,
            actor_name="시스템 관리자",
            detail=f"{mat_name} 입고 LOT 생성",
        )
        db.add(history)
    await db.flush()
    print(f"   LOT 완료 ({len(lot_ids)}개)")

    # ── 7. 입고 이력 20개 ────────────────────────────
    print("7. 원자재 입고 이력 20개 삽입...")
    existing_receipts = (await db.execute(
        select(RawMaterialReceipt.receipt_number)
    )).scalars().all()
    sup_code_list = list(supplier_ids.keys())

    for i in range(20):
        rnum = f"RCV-2026-{(i+1):04d}"
        if rnum in existing_receipts:
            continue
        mat_idx = i % len(mat_codes)
        mat_code = mat_codes[mat_idx]
        mat_name = MATERIAL_NAMES[mat_idx]
        sup_code = sup_codes[i % len(sup_codes)]
        price_per_unit = Decimal(str(MATERIALS[mat_idx][8]))
        qty = Decimal(str(round(random.uniform(200, 3000), 1)))
        receipt = RawMaterialReceipt(
            receipt_number=rnum,
            supplier_id=supplier_ids[sup_code],
            lot_id=lot_ids[i],
            material_name=mat_name,
            material_code=mat_code,
            quantity=qty,
            unit="kg",
            unit_price=price_per_unit,
            received_date=days_ago(20 - i),
            notes=f"{SUPPLIERS[i % len(SUPPLIERS)][1]} {mat_name} 정기 입고",
            created_by=admin_id,
        )
        db.add(receipt)
    await db.flush()
    print("   입고 이력 완료")

    # ── 8. 수주 20개 ─────────────────────────────────
    print("8. 수주 20개 삽입...")
    order_ids: list[uuid.UUID] = []
    existing_orders = (await db.execute(select(Order.order_number))).scalars().all()
    cust_code_list = list(customer_ids.keys())

    ORDER_STATUSES = [
        "received", "confirmed", "in_production", "shipped", "completed",
        "confirmed", "in_production", "received", "completed", "shipped",
        "received", "confirmed", "in_production", "completed", "cancelled",
        "received", "confirmed", "in_production", "shipped", "completed",
    ]
    for i in range(20):
        onum = f"ORD-2026-{(i+1):04d}"
        if onum in existing_orders:
            r = await db.execute(select(Order).where(Order.order_number == onum))
            order_ids.append(r.scalar_one().id)
            continue
        cust_code = cust_code_list[i % len(cust_code_list)]
        ordered = days_ago(20 - i)
        due = ordered + timedelta(days=random.randint(14, 45))
        qty = round(random.uniform(50, 500), 0)
        price = round(random.uniform(100000, 5000000), 0)
        order = Order(
            order_number=onum,
            customer_id=customer_ids[cust_code],
            status=ORDER_STATUSES[i],
            ordered_date=ordered,
            due_date=due,
            total_amount=Decimal(str(price * qty)),
            created_by=admin_id,
            notes=f"{PRODUCT_NAMES[i]} 발주",
        )
        db.add(order)
        await db.flush()
        order_ids.append(order.id)

        # 수주 아이템 1건
        mat_idx = i % len(mat_codes)
        item = OrderItem(
            order_id=order.id,
            material_code=mat_codes[mat_idx],
            material_name=MATERIAL_NAMES[mat_idx],
            quantity=qty,
            unit="개",
            unit_price=Decimal(str(price)),
        )
        db.add(item)
    await db.flush()
    print(f"   수주 완료 ({len(order_ids)}개)")

    # ── 9. 작업지시 20개 ─────────────────────────────
    print("9. 작업지시 20개 삽입...")
    existing_wo = (await db.execute(select(WorkOrder.wo_number))).scalars().all()
    prc_code_list = list(process_ids.keys())
    eqp_code_list = list(equipment_ids.keys())
    WO_STATUS_LIST = [
        "completed", "completed", "in_progress", "in_progress", "pending",
        "completed", "in_progress", "pending", "completed", "in_progress",
        "on_hold", "completed", "in_progress", "pending", "completed",
        "in_progress", "completed", "pending", "in_progress", "completed",
    ]
    for i in range(20):
        wonum = f"WO-2026-{(i+1):04d}"
        if wonum in existing_wo:
            continue
        prc_code = prc_code_list[i % len(prc_code_list)]
        eqp_code = eqp_code_list[i % len(eqp_code_list)]
        start_dt = dt_ago(20 - i, hours=8)
        wo_status = WO_STATUS_LIST[i]
        wo = WorkOrder(
            wo_number=wonum,
            lot_id=lot_ids[i],
            process_id=process_ids[prc_code],
            equipment_id=equipment_ids[eqp_code],
            assigned_to=admin_id,
            status=wo_status,
            planned_start=start_dt,
            planned_end=start_dt + timedelta(hours=random.randint(4, 24)),
            actual_start=start_dt if wo_status != "pending" else None,
            actual_end=start_dt + timedelta(hours=random.randint(3, 22)) if wo_status == "completed" else None,
            input_qty=round(random.uniform(100, 2000), 1),
            output_qty=round(random.uniform(90, 1950), 1),
            defect_qty=round(random.uniform(0, 50), 1),
            created_by=admin_id,
        )
        db.add(wo)
    await db.flush()
    print("   작업지시 완료")

    # ── 10. 품질 검사 20개 ──────────────────────────
    print("10. 품질 검사 20개 삽입...")
    existing_qi = (await db.execute(
        select(QualityInspection.lot_id)
    )).scalars().all()
    INSP_TYPES = ["incoming", "in_process", "final"]
    INSP_RESULTS = [
        "pass", "pass", "pass", "fail", "pass", "pass", "conditional_pass",
        "pass", "pass", "fail", "pass", "pass", "pass", "conditional_pass",
        "pass", "pass", "fail", "pass", "pass", "pass",
    ]
    DEFECT_TYPES = ["치수불량", "표면스크래치", "용접결함", "도장불량", "균열", "변형"]

    for i in range(20):
        lid = lot_ids[i]
        if lid in existing_qi:
            continue
        defect_rate = 0.0 if INSP_RESULTS[i] == "pass" else round(random.uniform(1.5, 8.0), 2)
        insp = QualityInspection(
            lot_id=lid,
            inspector_id=admin_id,
            inspection_type=INSP_TYPES[i % len(INSP_TYPES)],
            result=INSP_RESULTS[i],
            defect_rate=defect_rate,
            inspection_date=dt_ago(18 - i),
            notes=f"LOT {lot_display_ids[i]} 품질 검사 결과",
        )
        db.add(insp)
        await db.flush()

        if INSP_RESULTS[i] != "pass" and defect_rate > 0:
            dtype = random.choice(DEFECT_TYPES)
            defect = DefectDetail(
                inspection_id=insp.id,
                defect_code=f"DF-{(i+1):03d}",
                defect_type=dtype,
                qty=float(random.randint(1, 15)),
                description=f"검사 항목 {i+1}번 — {dtype} 발견",
            )
            db.add(defect)
    await db.flush()
    print("   품질 검사 완료")

    # ── 11. 출하 20개 ────────────────────────────────
    print("11. 출하 20개 삽입...")
    existing_ship = (await db.execute(select(Shipment.shipment_number))).scalars().all()
    SHIP_STATUSES = [
        "delivered", "delivered", "shipped", "shipped", "pending",
        "delivered", "shipped", "pending", "delivered", "shipped",
        "pending", "delivered", "shipped", "pending", "delivered",
        "shipped", "delivered", "pending", "shipped", "delivered",
    ]
    for i in range(20):
        snum = f"SHP-2026-{(i+1):04d}"
        if snum in existing_ship:
            continue
        cust_code = cust_code_list[i % len(cust_code_list)]
        planned = days_ago(15 - i)
        ship_status = SHIP_STATUSES[i]
        shipped_dt = dt_ago(14 - i) if ship_status in ("shipped", "delivered") else None
        delivered_dt = dt_ago(12 - i) if ship_status == "delivered" else None
        shipment = Shipment(
            shipment_number=snum,
            customer_id=customer_ids[cust_code],
            status=ship_status,
            planned_date=planned,
            shipped_date=shipped_dt,
            delivered_date=delivered_dt,
            notes=f"{CUSTOMER_NAMES[i % len(CUSTOMER_NAMES)]} 정기 출하",
            created_by=admin_id,
        )
        db.add(shipment)
        await db.flush()

        sl = ShipmentLot(
            shipment_id=shipment.id,
            lot_id=lot_ids[i],
            qty=round(random.uniform(50, 2000), 1),
            unit_price=round(random.uniform(10000, 500000), 0),
        )
        db.add(sl)
    await db.flush()
    print("   출하 완료")

    # ── 12. KPI 목표값 ──────────────────────────────
    print("12. KPI 목표값 삽입...")
    KPI_TARGETS = [
        ("defect_rate",            "1.50",  "%",    "daily"),
        ("equipment_utilization",  "90.00", "%",    "daily"),
        ("on_time_delivery",       "95.00", "%",    "monthly"),
        ("production_efficiency",  "88.00", "%",    "daily"),
        ("cycle_time_reduction",   "10.00", "%",    "monthly"),
        ("inventory_turnover",      "8.00", "회",   "monthly"),
        ("energy_efficiency",       "5.00", "%",    "monthly"),
        ("quality_cost_ratio",      "3.00", "%",    "monthly"),
        ("customer_satisfaction",  "95.00", "점",   "monthly"),
        ("lot_traceability",      "100.00", "%",    "daily"),
    ]
    existing_kpi = (await db.execute(select(KpiTarget.metric_key))).scalars().all()
    for metric_key, target_val, unit, period in KPI_TARGETS:
        if metric_key in existing_kpi:
            continue
        db.add(KpiTarget(
            metric_key=metric_key,
            target_value=Decimal(target_val),
            unit=unit,
            period=period,
            updated_by=admin_id,
        ))
    await db.flush()
    print("   KPI 목표값 완료")

    await db.commit()
    print("\n===== 시드 데이터 삽입 완료 =====\n")


async def main():
    async with AsyncSessionFactory() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
