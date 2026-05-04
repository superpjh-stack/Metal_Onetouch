"""Sprint 5 — 수주견적AI 기반 (파일 스토리지, CAD 분석, 단가 마스터, 견적)

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-04 19:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ENUM 타입 ──────────────────────────────────────────────────────────────
    op.execute(
        "CREATE TYPE cad_analysis_status_enum AS ENUM "
        "('pending','analyzing','completed','failed')"
    )
    op.execute(
        "CREATE TYPE quotation_status_enum AS ENUM "
        "('draft','submitted','accepted','rejected','expired')"
    )

    # ── uploaded_files ─────────────────────────────────────────────────────────
    op.create_table(
        "uploaded_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bucket", sa.String(100), nullable=False, server_default="metal-onetouch"),
        sa.Column("object_key", sa.String(500), nullable=False, unique=True),
        sa.Column("original_name", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_size", sa.BigInteger, nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_uploaded_files_hash",   "uploaded_files", ["file_hash"])
    op.create_index("ix_uploaded_files_by",      "uploaded_files", ["uploaded_by"])
    op.create_index("ix_uploaded_files_key",     "uploaded_files", ["object_key"], unique=True)

    # ── cad_drawings ───────────────────────────────────────────────────────────
    op.create_table(
        "cad_drawings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("drawing_number", sa.String(30), nullable=False, unique=True),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("uploaded_files.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("analysis_status", sa.Enum("pending", "analyzing", "completed", "failed", name="cad_analysis_status_enum", create_type=False), nullable=False, server_default="pending"),
        sa.Column("raw_result", postgresql.JSONB, nullable=True),
        sa.Column("parsed_objects", postgresql.JSONB, nullable=True),
        sa.Column("dimensions", postgresql.JSONB, nullable=True),
        sa.Column("material_hint", sa.String(100), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("analyzed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cad_file",     "cad_drawings", ["file_id"])
    op.create_index("ix_cad_customer", "cad_drawings", ["customer_id"])
    op.create_index("ix_cad_status",   "cad_drawings", ["analysis_status"])
    op.create_index("ix_cad_number",   "cad_drawings", ["drawing_number"], unique=True)

    # ── process_price_master ───────────────────────────────────────────────────
    op.create_table(
        "process_price_master",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("process_type", sa.String(50), nullable=False),
        sa.Column("material_grade", sa.String(50), nullable=True),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("price_unit", sa.String(30), nullable=False),
        sa.Column("effective_from", sa.Date, nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_price_process_type", "process_price_master", ["process_type"])
    # COALESCE unique — PostgreSQL expression index
    op.execute(
        "CREATE UNIQUE INDEX ix_price_process_material "
        "ON process_price_master(process_type, COALESCE(material_grade, ''))"
    )

    # ── material_price_master ──────────────────────────────────────────────────
    op.create_table(
        "material_price_master",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("material_code", sa.String(50), nullable=False, unique=True),
        sa.Column("material_name", sa.String(200), nullable=False),
        sa.Column("price_per_kg", sa.Numeric(12, 4), nullable=False),
        sa.Column("density", sa.Numeric(8, 4), nullable=False, server_default="7.93"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_material_price_code", "material_price_master", ["material_code"], unique=True)

    # ── quotations ─────────────────────────────────────────────────────────────
    op.create_table(
        "quotations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("quotation_number", sa.String(30), nullable=False, unique=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("drawing_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cad_drawings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.Enum("draft", "submitted", "accepted", "rejected", "expired", name="quotation_status_enum", create_type=False), nullable=False, server_default="draft"),
        sa.Column("material_cost", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("process_cost", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("margin_rate", sa.Numeric(5, 3), nullable=False, server_default="0.15"),
        sa.Column("final_amount", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("valid_until", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_quotation_customer", "quotations", ["customer_id"])
    op.create_index("ix_quotation_drawing",  "quotations", ["drawing_id"])
    op.create_index("ix_quotation_order",    "quotations", ["order_id"])
    op.create_index("ix_quotation_status",   "quotations", ["status"])
    op.create_index("ix_quotation_number",   "quotations", ["quotation_number"], unique=True)

    # ── quotation_items ────────────────────────────────────────────────────────
    op.create_table(
        "quotation_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("quotation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_type", sa.String(50), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False, server_default="1"),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("amount", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_quotation_items_qid", "quotation_items", ["quotation_id"])

    # ── 시드 데이터: 공정 단가 (6행) ──────────────────────────────────────────
    op.execute("""
        INSERT INTO process_price_master (process_type, material_grade, unit_price, price_unit, notes)
        VALUES
            ('cutting',  NULL,     5.0,    'per_mm',    '기본 절단 단가 (원/mm)'),
            ('drilling', NULL,     800.0,  'per_piece',  '기본 홀가공 단가 (원/개)'),
            ('bending',  NULL,     1500.0, 'per_count',  '기본 절곡 단가 (원/회)'),
            ('welding',  NULL,     8.0,    'per_mm',    '기본 용접 단가 (원/mm)'),
            ('painting', NULL,     2000.0, 'per_sqm',   '기본 도장 단가 (원/㎡)'),
            ('surface',  'SUS304', 3500.0, 'per_sqm',   'SUS304 표면처리 (원/㎡)')
    """)

    # ── 시드 데이터: 재질 단가 (5행) ──────────────────────────────────────────
    op.execute("""
        INSERT INTO material_price_master (material_code, material_name, price_per_kg, density)
        VALUES
            ('SUS304', 'SUS304 스테인리스강',    4500.0, 7.93),
            ('SUS316', 'SUS316 스테인리스강',    6000.0, 8.00),
            ('SS400',  'SS400 일반구조용강',     1200.0, 7.85),
            ('AL6061', '알루미늄합금 6061',      8000.0, 2.70),
            ('SPCC',   'SPCC 냉간압연강판',      1500.0, 7.85)
    """)


def downgrade() -> None:
    op.drop_table("quotation_items")
    op.drop_table("quotations")
    op.drop_table("material_price_master")
    op.drop_table("process_price_master")
    op.drop_table("cad_drawings")
    op.drop_table("uploaded_files")
    op.execute("DROP TYPE IF EXISTS quotation_status_enum")
    op.execute("DROP TYPE IF EXISTS cad_analysis_status_enum")
