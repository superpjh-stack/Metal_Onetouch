"""Initial schema — users, lots, lot_histories

Revision ID: 0001
Revises:
Create Date: 2026-04-30 09:00:00.000000

This migration captures the Sprint 1 state:
  - users table (single-role RBAC, status enum)
  - lots table (LOT master with state machine)
  - lot_histories table (immutable audit trail)

Note: Generated manually to match the async SQLAlchemy setup in env.py.
N:M user_roles table is planned for Sprint 3 — see user.py comment.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision: str = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # ENUM types (PostgreSQL requires explicit CREATE TYPE)
    # ------------------------------------------------------------------
    user_role_enum = sa.Enum(
        "production_manager",
        "quality_inspector",
        "process_engineer",
        "executive",
        "sales_engineer",
        "admin",
        name="user_role_enum",
    )
    user_role_enum.create(op.get_bind(), checkfirst=True)

    user_status_enum = sa.Enum(
        "active",
        "inactive",
        "suspended",
        name="user_status_enum",
    )
    user_status_enum.create(op.get_bind(), checkfirst=True)

    lot_status_enum = sa.Enum(
        "created",
        "in_receipt",
        "received",
        "in_process",
        "in_inspection",
        "completed",
        "shipped",
        "on_hold",
        "rejected",
        "cancelled",
        name="lot_status_enum",
    )
    lot_status_enum.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "production_manager",
                "quality_inspector",
                "process_engineer",
                "executive",
                "sales_engineer",
                "admin",
                name="user_role_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="production_manager",
        ),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("employee_no", sa.String(20), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "inactive",
                "suspended",
                name="user_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # ------------------------------------------------------------------
    # lots
    # ------------------------------------------------------------------
    op.create_table(
        "lots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("lot_id", sa.String(20), nullable=False),
        sa.Column(
            "lot_status",
            sa.Enum(
                "created",
                "in_receipt",
                "received",
                "in_process",
                "in_inspection",
                "completed",
                "shipped",
                "on_hold",
                "rejected",
                "cancelled",
                name="lot_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="created",
        ),
        sa.Column("raw_material_id", sa.String(50), nullable=True),
        sa.Column("raw_material_name", sa.String(200), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("customer_name", sa.String(200), nullable=True),
        sa.Column("product_code", sa.String(50), nullable=True),
        sa.Column("product_name", sa.String(200), nullable=True),
        sa.Column("order_number", sa.String(50), nullable=True),
        sa.Column("planned_start_date", sa.Date(), nullable=True),
        sa.Column("planned_end_date", sa.Date(), nullable=True),
        sa.Column("actual_start_date", sa.Date(), nullable=True),
        sa.Column("actual_end_date", sa.Date(), nullable=True),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lots_lot_id"), "lots", ["lot_id"], unique=True)
    op.create_index(op.f("ix_lots_lot_status"), "lots", ["lot_status"], unique=False)
    op.create_index(
        op.f("ix_lots_raw_material_id"), "lots", ["raw_material_id"], unique=False
    )

    # PostgreSQL rule: forbid DELETE on lots (soft-delete via status only)
    op.execute(
        """
        CREATE RULE no_delete_lots AS
            ON DELETE TO lots
            DO INSTEAD NOTHING
        """
    )

    # ------------------------------------------------------------------
    # lot_histories
    # ------------------------------------------------------------------
    op.create_table(
        "lot_histories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("lot_id_fk", sa.UUID(), nullable=False),
        sa.Column("lot_display_id", sa.String(20), nullable=False),
        sa.Column("step", sa.String(100), nullable=False),
        sa.Column("from_status", sa.String(30), nullable=True),
        sa.Column("to_status", sa.String(30), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("actor_name", sa.String(100), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lot_id_fk"], ["lots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_lot_histories_lot_id_fk"),
        "lot_histories",
        ["lot_id_fk"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lot_histories_lot_display_id"),
        "lot_histories",
        ["lot_display_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lot_histories_created_at"),
        "lot_histories",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("lot_histories")

    op.execute("DROP RULE IF EXISTS no_delete_lots ON lots")
    op.drop_table("lots")

    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS lot_status_enum")
    op.execute("DROP TYPE IF EXISTS user_status_enum")
    op.execute("DROP TYPE IF EXISTS user_role_enum")
