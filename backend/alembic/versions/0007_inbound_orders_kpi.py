"""Sprint 4 — 입고관리, 수주, KPI 테이블

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-04 16:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # order_status_enum
    op.execute(
        "CREATE TYPE order_status_enum AS ENUM "
        "('received','confirmed','in_production','shipped','completed','cancelled')"
    )

    # raw_material_receipts — 원자재 입고 이력
    op.create_table(
        "raw_material_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("receipt_number", sa.String(30), nullable=False, unique=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("material_name", sa.String(200), nullable=False),
        sa.Column("material_code", sa.String(50), nullable=True),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False, server_default="kg"),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("received_date", sa.Date, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_receipt_number",   "raw_material_receipts", ["receipt_number"], unique=True)
    op.create_index("ix_receipt_supplier", "raw_material_receipts", ["supplier_id"])
    op.create_index("ix_receipt_lot",      "raw_material_receipts", ["lot_id"])
    op.create_index("ix_receipt_date",     "raw_material_receipts", ["received_date"])

    # orders — 수주
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_number", sa.String(30), nullable=False, unique=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", postgresql.ENUM(name="order_status_enum", create_type=False), nullable=False, server_default="received"),
        sa.Column("ordered_date", sa.Date, nullable=False),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("total_amount", sa.Numeric(16, 2), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_order_number",   "orders", ["order_number"], unique=True)
    op.create_index("ix_order_customer", "orders", ["customer_id"])
    op.create_index("ix_order_status",   "orders", ["status"])
    op.create_index("ix_order_due",      "orders", ["due_date"])

    # order_items — 수주 라인
    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_name", sa.String(200), nullable=False),
        sa.Column("material_code", sa.String(50), nullable=True),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False, server_default="ea"),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_order_item_order", "order_items", ["order_id"])
    op.create_index("ix_order_item_lot",   "order_items", ["lot_id"])

    # kpi_targets — KPI 목표값
    op.create_table(
        "kpi_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("metric_key", sa.String(50), nullable=False, unique=True),
        sa.Column("target_value", sa.Numeric(10, 4), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False, server_default="%"),
        sa.Column("period", sa.String(10), nullable=False, server_default="daily"),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_kpi_key", "kpi_targets", ["metric_key"], unique=True)

    # 초기 KPI 목표값 시드
    op.execute("""
        INSERT INTO kpi_targets (metric_key, target_value, unit, period) VALUES
        ('production_rate',       100.0, '%',   'daily'),
        ('defect_rate',             2.0, '%',   'daily'),
        ('delivery_rate',          95.0, '%',   'monthly'),
        ('equipment_utilization',  80.0, '%',   'daily')
    """)


def downgrade() -> None:
    op.drop_table("kpi_targets")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("raw_material_receipts")
    op.execute("DROP TYPE order_status_enum")
