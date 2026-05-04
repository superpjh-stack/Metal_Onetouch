"""Work orders, process results, and system audit logs

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-30 11:00:00.000000

Sprint 2 — 작업지시 및 감사 로그 테이블 생성:
  - work_orders (작업지시)
  - process_results (공정 실적, 불변 레코드 — updated_at 없음)
  - system_logs (시스템 감사 로그)
"""
from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # ENUM types
    # ------------------------------------------------------------------
    wo_status_enum = sa.Enum(
        "pending",
        "in_progress",
        "completed",
        "on_hold",
        "cancelled",
        name="wo_status_enum",
    )
    wo_status_enum.create(op.get_bind(), checkfirst=True)

    audit_action_enum = sa.Enum(
        "CREATE",
        "UPDATE",
        "DELETE",
        "LOGIN",
        "LOGOUT",
        "LOGIN_FAILED",
        "EXPORT",
        "IMPORT",
        "STATUS_CHANGE",
        name="audit_action_enum",
    )
    audit_action_enum.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------
    # work_orders
    # ------------------------------------------------------------------
    op.create_table(
        "work_orders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("wo_number", sa.String(30), nullable=False),
        sa.Column("lot_id", sa.UUID(), nullable=False),
        sa.Column("process_id", sa.UUID(), nullable=False),
        sa.Column("equipment_id", sa.UUID(), nullable=True),
        sa.Column("assigned_to", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "in_progress",
                "completed",
                "on_hold",
                "cancelled",
                name="wo_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("planned_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_qty", sa.Numeric(12, 3), nullable=True),
        sa.Column("output_qty", sa.Numeric(12, 3), nullable=True),
        sa.Column(
            "defect_qty", sa.Numeric(12, 3), nullable=False, server_default="0"
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["process_id"], ["processes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_work_orders_wo_number"), "work_orders", ["wo_number"], unique=True
    )
    op.create_index(
        op.f("ix_work_orders_lot_id"), "work_orders", ["lot_id"], unique=False
    )
    op.create_index(
        op.f("ix_work_orders_assigned_to"),
        "work_orders",
        ["assigned_to"],
        unique=False,
    )
    op.create_index(
        op.f("ix_work_orders_status"), "work_orders", ["status"], unique=False
    )

    # ------------------------------------------------------------------
    # process_results (불변 레코드 — updated_at 컬럼 없음)
    # ------------------------------------------------------------------
    op.create_table(
        "process_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("work_order_id", sa.UUID(), nullable=False),
        sa.Column("lot_id", sa.UUID(), nullable=False),
        sa.Column("equipment_id", sa.UUID(), nullable=True),
        sa.Column("worker_id", sa.UUID(), nullable=True),
        sa.Column("input_qty", sa.Numeric(12, 3), nullable=False),
        sa.Column("output_qty", sa.Numeric(12, 3), nullable=False),
        sa.Column(
            "defect_qty", sa.Numeric(12, 3), nullable=False, server_default="0"
        ),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("condition_notes", sa.Text(), nullable=True),
        sa.Column("defect_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["equipment_id"], ["equipment.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["work_order_id"], ["work_orders.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["worker_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_process_results_work_order_id"),
        "process_results",
        ["work_order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_process_results_lot_id"),
        "process_results",
        ["lot_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # system_logs
    # ------------------------------------------------------------------
    op.create_table(
        "system_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("actor_name", sa.String(100), nullable=True),
        sa.Column(
            "action",
            sa.Enum(
                "CREATE",
                "UPDATE",
                "DELETE",
                "LOGIN",
                "LOGOUT",
                "LOGIN_FAILED",
                "EXPORT",
                "IMPORT",
                "STATUS_CHANGE",
                name="audit_action_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("trace_id", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_system_logs_actor_id"), "system_logs", ["actor_id"], unique=False
    )
    op.create_index(
        op.f("ix_system_logs_action"), "system_logs", ["action"], unique=False
    )
    op.create_index(
        op.f("ix_system_logs_created_at"), "system_logs", ["created_at"], unique=False
    )


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_index(op.f("ix_system_logs_created_at"), table_name="system_logs")
    op.drop_index(op.f("ix_system_logs_action"), table_name="system_logs")
    op.drop_index(op.f("ix_system_logs_actor_id"), table_name="system_logs")
    op.drop_table("system_logs")

    op.drop_index(
        op.f("ix_process_results_lot_id"), table_name="process_results"
    )
    op.drop_index(
        op.f("ix_process_results_work_order_id"), table_name="process_results"
    )
    op.drop_table("process_results")

    op.drop_index(op.f("ix_work_orders_status"), table_name="work_orders")
    op.drop_index(op.f("ix_work_orders_assigned_to"), table_name="work_orders")
    op.drop_index(op.f("ix_work_orders_lot_id"), table_name="work_orders")
    op.drop_index(op.f("ix_work_orders_wo_number"), table_name="work_orders")
    op.drop_table("work_orders")

    # Drop ENUMs in reverse order
    op.execute("DROP TYPE IF EXISTS audit_action_enum")
    op.execute("DROP TYPE IF EXISTS wo_status_enum")
