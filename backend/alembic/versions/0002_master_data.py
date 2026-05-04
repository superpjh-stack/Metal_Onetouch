"""Master data tables: suppliers, customers, raw_materials, processes, equipment

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-30 10:00:00.000000

Sprint 2 — 기준정보(마스터 데이터) 테이블 생성:
  - suppliers (공급업체)
  - customers (고객사)
  - raw_materials (원자재)
  - processes (공정)
  - equipment (설비)
"""
from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # ENUM types
    # ------------------------------------------------------------------
    supplier_grade_enum = sa.Enum("A", "B", "C", "D", name="supplier_grade_enum")
    supplier_grade_enum.create(op.get_bind(), checkfirst=True)

    material_category_enum = sa.Enum(
        "steel_sheet",
        "stainless",
        "aluminum",
        "copper",
        "pipe",
        "bar",
        "other",
        name="material_category_enum",
    )
    material_category_enum.create(op.get_bind(), checkfirst=True)

    process_type_enum = sa.Enum(
        "cutting",
        "forming",
        "welding",
        "painting",
        "inspection",
        "assembly",
        "other",
        name="process_type_enum",
    )
    process_type_enum.create(op.get_bind(), checkfirst=True)

    equipment_status_enum = sa.Enum(
        "running",
        "idle",
        "maintenance",
        "breakdown",
        "decommissioned",
        name="equipment_status_enum",
    )
    equipment_status_enum.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------
    # suppliers
    # ------------------------------------------------------------------
    op.create_table(
        "suppliers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("supplier_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("contact_person", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column(
            "grade",
            sa.Enum("A", "B", "C", "D", name="supplier_grade_enum", create_type=False),
            nullable=False,
            server_default="C",
        ),
        sa.Column("business_no", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
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
    op.create_index(
        op.f("ix_suppliers_supplier_code"), "suppliers", ["supplier_code"], unique=True
    )
    op.create_index(op.f("ix_suppliers_name"), "suppliers", ["name"], unique=False)

    # ------------------------------------------------------------------
    # customers
    # ------------------------------------------------------------------
    op.create_table(
        "customers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("customer_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("contact_person", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("business_no", sa.String(20), nullable=True),
        sa.Column("credit_limit", sa.Numeric(15, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
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
    op.create_index(
        op.f("ix_customers_customer_code"),
        "customers",
        ["customer_code"],
        unique=True,
    )
    op.create_index(op.f("ix_customers_name"), "customers", ["name"], unique=False)

    # ------------------------------------------------------------------
    # raw_materials
    # ------------------------------------------------------------------
    op.create_table(
        "raw_materials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("material_code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "steel_sheet",
                "stainless",
                "aluminum",
                "copper",
                "pipe",
                "bar",
                "other",
                name="material_category_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="other",
        ),
        sa.Column("spec", sa.String(200), nullable=True),
        sa.Column("unit", sa.String(20), nullable=False, server_default="EA"),
        sa.Column("supplier_id", sa.UUID(), nullable=True),
        sa.Column("stock_qty", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column(
            "min_stock_qty", sa.Numeric(12, 3), nullable=False, server_default="0"
        ),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_raw_materials_material_code"),
        "raw_materials",
        ["material_code"],
        unique=True,
    )
    op.create_index(
        op.f("ix_raw_materials_name"), "raw_materials", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_raw_materials_supplier_id"),
        "raw_materials",
        ["supplier_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # processes
    # ------------------------------------------------------------------
    op.create_table(
        "processes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("process_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "process_type",
            sa.Enum(
                "cutting",
                "forming",
                "welding",
                "painting",
                "inspection",
                "assembly",
                "other",
                name="process_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("std_time_min", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
    op.create_index(
        op.f("ix_processes_process_code"), "processes", ["process_code"], unique=True
    )

    # ------------------------------------------------------------------
    # equipment
    # ------------------------------------------------------------------
    op.create_table(
        "equipment",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("equipment_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("process_id", sa.UUID(), nullable=True),
        sa.Column("manufacturer", sa.String(100), nullable=True),
        sa.Column("model_no", sa.String(100), nullable=True),
        sa.Column("serial_no", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "running",
                "idle",
                "maintenance",
                "breakdown",
                "decommissioned",
                name="equipment_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="idle",
        ),
        sa.Column("installed_at", sa.Date(), nullable=True),
        sa.Column("last_maint_at", sa.Date(), nullable=True),
        sa.Column("next_maint_at", sa.Date(), nullable=True),
        sa.Column("location", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["process_id"], ["processes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_equipment_equipment_code"),
        "equipment",
        ["equipment_code"],
        unique=True,
    )
    op.create_index(
        op.f("ix_equipment_process_id"), "equipment", ["process_id"], unique=False
    )


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_index(op.f("ix_equipment_process_id"), table_name="equipment")
    op.drop_index(op.f("ix_equipment_equipment_code"), table_name="equipment")
    op.drop_table("equipment")

    op.drop_index(op.f("ix_processes_process_code"), table_name="processes")
    op.drop_table("processes")

    op.drop_index(op.f("ix_raw_materials_supplier_id"), table_name="raw_materials")
    op.drop_index(op.f("ix_raw_materials_name"), table_name="raw_materials")
    op.drop_index(op.f("ix_raw_materials_material_code"), table_name="raw_materials")
    op.drop_table("raw_materials")

    op.drop_index(op.f("ix_customers_name"), table_name="customers")
    op.drop_index(op.f("ix_customers_customer_code"), table_name="customers")
    op.drop_table("customers")

    op.drop_index(op.f("ix_suppliers_name"), table_name="suppliers")
    op.drop_index(op.f("ix_suppliers_supplier_code"), table_name="suppliers")
    op.drop_table("suppliers")

    # Drop ENUMs in reverse order
    op.execute("DROP TYPE IF EXISTS equipment_status_enum")
    op.execute("DROP TYPE IF EXISTS process_type_enum")
    op.execute("DROP TYPE IF EXISTS material_category_enum")
    op.execute("DROP TYPE IF EXISTS supplier_grade_enum")
