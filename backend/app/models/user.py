import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

# RBAC 역할 정의
# NOTE: N:M user_roles planned for Sprint 3 — single role used in Sprint 1-2 for simplicity.
# Design reference: docs/02-design/db/schema.sql (users → user_roles → roles)
VALID_ROLES = (
    "production_manager",
    "quality_inspector",
    "process_engineer",
    "executive",
    "sales_engineer",
    "admin",
)

# 사용자 상태 정의 (설계: docs/02-design/db/schema.sql)
USER_STATUS_VALUES = (
    "active",      # 정상 활성
    "inactive",    # 비활성 (퇴직 등)
    "suspended",   # 일시 정지
)


class User(Base, UUIDMixin, TimestampMixin):
    """
    사용자 계정 모델

    RBAC 참고:
    - Sprint 1-2: 단일 role 컬럼 (simple enum)
    - Sprint 3 예정: N:M user_roles 테이블로 마이그레이션
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum(*VALID_ROLES, name="user_role_enum"),
        nullable=False,
        default="production_manager",
    )
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    employee_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # status 대신 is_active는 Sprint 1 구현에서 사용했으나, 설계 표준(active/inactive/suspended)으로 변경
    status: Mapped[str] = mapped_column(
        Enum(*USER_STATUS_VALUES, name="user_status_enum"),
        nullable=False,
        default="active",
    )
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    lot_histories: Mapped[list["LotHistory"]] = relationship(  # noqa: F821
        "LotHistory", back_populates="actor", lazy="select"
    )

    @property
    def is_active(self) -> bool:
        """하위 호환성 프로퍼티 — status == 'active'인 경우 True를 반환합니다."""
        return self.status == "active"

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role}) [{self.status}]>"
