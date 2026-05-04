"""Sprint 6 — Vision ML (어노테이션, 데이터셋, 학습잡, DXF 매핑, BOM)

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-04 23:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # annotation_tasks
    op.create_table(
        "annotation_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("drawing_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cad_drawings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("original_parsed", postgresql.JSONB(), nullable=False),
        sa.Column("corrected_parsed", postgresql.JSONB(), nullable=True),
        sa.Column("annotator_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("skip_reason", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_annot_drawing", "annotation_tasks", ["drawing_id"])
    op.create_index("ix_annot_status", "annotation_tasks", ["status"])
    op.create_index("ix_annot_annotator", "annotation_tasks", ["annotator_id"])

    # annotation_datasets
    op.create_table(
        "annotation_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("version", sa.String(20), nullable=False, unique=True),
        sa.Column("image_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("label_counts", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("s3_path", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="building"),
        sa.Column("built_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # training_jobs
    op.create_table(
        "training_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("annotation_datasets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("model_version", sa.String(20), nullable=False, server_default="yolov8s"),
        sa.Column("epochs", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("batch_size", sa.Integer(), nullable=False, server_default="16"),
        sa.Column("img_size", sa.Integer(), nullable=False, server_default="640"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("train_map50", sa.Numeric(6, 4), nullable=True),
        sa.Column("val_map50", sa.Numeric(6, 4), nullable=True),
        sa.Column("model_s3_path", sa.String(500), nullable=True),
        sa.Column("mlflow_run_id", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("hyperparams", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_train_dataset", "training_jobs", ["dataset_id"])
    op.create_index("ix_train_status", "training_jobs", ["status"])
    op.create_index(
        "ix_train_active",
        "training_jobs",
        ["is_active"],
        postgresql_where=sa.text("is_active = TRUE"),
    )

    # dxf_layer_mappings
    op.create_table(
        "dxf_layer_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("layer_pattern", sa.String(100), nullable=False),
        sa.Column("process_type", sa.String(50), nullable=False),
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_dxf_pattern",
        "dxf_layer_mappings",
        ["layer_pattern"],
        unique=True,
        postgresql_where=sa.text("is_active = TRUE"),
    )

    # bom_headers
    op.create_table(
        "bom_headers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("quotation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quotations.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("revision", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("total_weight_kg", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_bom_quotation", "bom_headers", ["quotation_id"])
    op.create_index("ix_bom_order", "bom_headers", ["order_id"])

    # bom_items
    op.create_table(
        "bom_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bom_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bom_headers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_code", sa.String(50), nullable=False),
        sa.Column("specification", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False, server_default="1"),
        sa.Column("unit", sa.String(20), nullable=False, server_default="kg"),
        sa.Column("unit_weight_kg", sa.Numeric(10, 4), nullable=True),
        sa.Column("total_weight_kg", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_bom_items_bom", "bom_items", ["bom_id"])

    # 시드: DXF 레이어 매핑 7개
    op.execute("""
        INSERT INTO dxf_layer_mappings (layer_pattern, process_type, priority) VALUES
        ('HOLE*',   'drilling', 10),
        ('DRILL*',  'drilling',  9),
        ('BEND*',   'bending',  10),
        ('FOLD*',   'bending',   9),
        ('CUT*',    'cutting',  10),
        ('*SLOT*',  'cutting',   8),
        ('WELD*',   'welding',  10)
    """)


def downgrade() -> None:
    op.drop_table("bom_items")
    op.drop_table("bom_headers")
    op.drop_table("dxf_layer_mappings")
    op.drop_table("training_jobs")
    op.drop_table("annotation_datasets")
    op.drop_table("annotation_tasks")
