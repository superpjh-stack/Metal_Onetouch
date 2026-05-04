import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    event,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

# LOT 상태 정의
LOT_STATUS_VALUES = (
    "created",        # LOT 생성됨
    "in_receipt",     # 입고 처리 중
    "received",       # 입고 완료
    "in_process",     # 가공 중
    "in_inspection",  # 검사 중
    "completed",      # 완료
    "shipped",        # 출하됨 (Sprint 3)
    "delivered",      # 인수 완료 (Sprint 3)
    "on_hold",        # 보류
    "rejected",       # 불합격 (Sprint 3: in_process에서도 직접 전환 가능)
    "cancelled",      # 취소 (삭제 대신 사용 — DB 레벨 no_delete_lots 룰과 일치)
)

# 최종 상태 — 한번 진입하면 다른 상태로 전환 불가
LOT_FINAL_STATUSES = frozenset({"delivered", "rejected", "cancelled"})

# 허용된 상태 전환 맵
LOT_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "created":       ["in_receipt", "on_hold", "cancelled"],
    "in_receipt":    ["received", "on_hold", "cancelled"],
    "received":      ["in_process", "on_hold", "cancelled"],
    "in_process":    ["in_inspection", "rejected", "on_hold", "cancelled"],  # Sprint 3: rejected 직접 전환
    "in_inspection": ["completed", "rejected", "on_hold", "cancelled"],
    "completed":     ["shipped"],
    "shipped":       ["delivered"],   # Sprint 3
    "delivered":     [],              # Sprint 3: 종료 상태
    "on_hold":       ["created", "in_receipt", "received", "in_process", "in_inspection", "cancelled"],
    "rejected":      [],
    "cancelled":     [],
}


class Lot(Base, UUIDMixin, TimestampMixin):
    """
    LOT 마스터 모델

    lot_id 형식: L{YYYYMMDD}-{4자리 SEQ}
    예) L20260430-0001
    """

    __tablename__ = "lots"

    lot_id: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    lot_status: Mapped[str] = mapped_column(
        Enum(*LOT_STATUS_VALUES, name="lot_status_enum"),
        nullable=False,
        default="created",
        index=True,
    )

    # 원자재 정보
    raw_material_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    raw_material_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # 고객/제품 정보
    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    product_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    product_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    order_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 일정
    planned_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    planned_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # 비고
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 생성자
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    histories: Mapped[list["LotHistory"]] = relationship(
        "LotHistory",
        back_populates="lot",
        order_by="LotHistory.created_at",
        lazy="select",
    )
    quality_inspections: Mapped[list["QualityInspection"]] = relationship(  # noqa: F821
        "QualityInspection",
        back_populates="lot",
        order_by="QualityInspection.inspection_date",
        lazy="select",
    )

    @classmethod
    async def generate_lot_id(cls, session: AsyncSession) -> str:
        """
        'L{YYYYMMDD}-{4자리 SEQ}' 형식의 LOT ID를 생성합니다.
        당일 생성된 LOT 수를 카운트해 순번을 부여합니다.
        """
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"L{today}-"

        # 당일 가장 큰 lot_id 조회
        result = await session.execute(
            select(func.count(Lot.id)).where(Lot.lot_id.like(f"{prefix}%"))
        )
        count = result.scalar_one() or 0
        seq = count + 1
        return f"{prefix}{seq:04d}"

    def can_transition_to(self, new_status: str) -> bool:
        """현재 상태에서 new_status로 전환 가능한지 확인."""
        allowed = LOT_STATUS_TRANSITIONS.get(self.lot_status, [])
        return new_status in allowed

    def __repr__(self) -> str:
        return f"<Lot {self.lot_id} [{self.lot_status}]>"


# ------------------------------------------------------------------------------
# DB-level delete guard (app-side enforcement of no_delete_lots DB rule)
# ------------------------------------------------------------------------------

@event.listens_for(Lot, "before_delete")
def _prevent_lot_delete(mapper, connection, target: "Lot") -> None:
    """
    LOT 삭제를 앱 레벨에서 차단합니다.

    설계 정책 (docs/02-design/db/schema.sql):
        CREATE RULE no_delete_lots AS ON DELETE TO lots DO INSTEAD NOTHING

    DB 룰이 조용히 무시하는 것과 달리, 이 리스너는 예외를 발생시켜
    개발자가 실수로 session.delete(lot)을 호출했을 때 즉시 인지할 수 있게 합니다.
    LOT을 비활성화하려면 status를 'cancelled'로 변경하세요.
    """
    # 임포트를 지연해 순환 임포트를 방지합니다
    from app.core.exceptions import LotDeleteForbiddenException  # noqa: PLC0415
    raise LotDeleteForbiddenException(
        f"LOT '{target.lot_id}' 삭제가 차단되었습니다. "
        "status를 'cancelled'로 변경하는 POST /{lot_id}/cancel 엔드포인트를 사용하세요."
    )


class LotHistory(Base, UUIDMixin):
    """LOT 상태 변경 이력 모델"""

    __tablename__ = "lot_histories"

    lot_id_fk: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lot_display_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # 이력 항목
    step: Mapped[str] = mapped_column(String(100), nullable=False)
    from_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    to_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    lot: Mapped["Lot"] = relationship("Lot", back_populates="histories")
    actor: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User", back_populates="lot_histories", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<LotHistory {self.lot_display_id} {self.step}>"
