"""Sprint 3 — 품질검사 + 출하물류 테이블 + LOT 상태 확장

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-04 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # LOT 상태 enum에 delivered 추가
    op.execute("ALTER TYPE lot_status_enum ADD VALUE IF NOT EXISTS 'delivered' AFTER 'shipped'")

    # quality_inspections
    op.create_table(
        "quality_inspections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("inspector_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("inspection_type", sa.String(20), nullable=False),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("defect_rate", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("inspection_date", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_qi_lot",        "quality_inspections", ["lot_id"])
    op.create_index("ix_qi_inspector",  "quality_inspections", ["inspector_id"])
    op.create_index("ix_qi_result",     "quality_inspections", ["result"])
    op.create_index("ix_qi_date",       "quality_inspections", ["inspection_date"])
    op.create_index("ix_qi_type",       "quality_inspections", ["inspection_type"])

    # defect_details
    op.create_table(
        "defect_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("inspection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quality_inspections.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("defect_code", sa.String(30), nullable=False),
        sa.Column("defect_type", sa.String(20), nullable=False),
        sa.Column("qty", sa.Numeric(12, 3), nullable=False, server_default="1"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("root_cause", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_dd_inspection", "defect_details", ["inspection_id"])
    op.create_index("ix_dd_type",       "defect_details", ["defect_type"])
    op.create_index("ix_dd_code",       "defect_details", ["defect_code"])

    # shipments
    op.create_table(
        "shipments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("shipment_number", sa.String(30), nullable=False, unique=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("planned_date", sa.Date, nullable=True),
        sa.Column("shipped_date", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("delivered_date", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_sh_number",   "shipments", ["shipment_number"])
    op.create_index("ix_sh_customer", "shipments", ["customer_id"])
    op.create_index("ix_sh_status",   "shipments", ["status"])
    op.create_index("ix_sh_planned",  "shipments", ["planned_date"])

    # shipment_lots
    op.create_table(
        "shipment_lots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("qty", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("shipment_id", "lot_id", name="uq_shipment_lot"),
    )
    op.create_index("ix_sl_shipment", "shipment_lots", ["shipment_id"])
    op.create_index("ix_sl_lot",      "shipment_lots", ["lot_id"])


def downgrade() -> None:
    op.drop_table("shipment_lots")
    op.drop_table("shipments")
    op.drop_table("defect_details")
    op.drop_table("quality_inspections")
    # delivered enum 값은 PostgreSQL에서 DROP 불가 (무시)
