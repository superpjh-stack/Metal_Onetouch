"""Sprint 2 — 누락 인덱스 9개 추가

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-04 00:00:00.000000

추가 인덱스:
  - ix_suppliers_grade           : suppliers(grade)
  - ix_raw_materials_category    : raw_materials(category)
  - ix_processes_type            : processes(process_type)
  - ix_equipment_status          : equipment(status)
  - ix_wo_process                : work_orders(process_id)
  - ix_wo_planned                : work_orders(planned_start)
  - ix_pr_worker                 : process_results(worker_id)
  - ix_pr_start_time             : process_results(start_time)
  - ix_syslog_resource           : system_logs(resource_type, resource_id) 복합
"""
from alembic import op


revision: str = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # suppliers — 등급별 필터링 최적화
    op.create_index("ix_suppliers_grade", "suppliers", ["grade"], unique=False)

    # raw_materials — 카테고리별 조회 최적화
    op.create_index(
        "ix_raw_materials_category", "raw_materials", ["category"], unique=False
    )

    # processes — 공정 유형별 필터링 최적화
    op.create_index(
        "ix_processes_type", "processes", ["process_type"], unique=False
    )

    # equipment — 상태별 조회 최적화
    op.create_index("ix_equipment_status", "equipment", ["status"], unique=False)

    # work_orders — 공정별 작업지시 조회 최적화
    op.create_index(
        "ix_wo_process", "work_orders", ["process_id"], unique=False
    )

    # work_orders — 계획 시작일 기반 스케줄 조회 최적화
    op.create_index(
        "ix_wo_planned", "work_orders", ["planned_start"], unique=False
    )

    # process_results — 작업자별 실적 조회 최적화
    op.create_index(
        "ix_pr_worker", "process_results", ["worker_id"], unique=False
    )

    # process_results — 시간 범위 조회 최적화
    op.create_index(
        "ix_pr_start_time", "process_results", ["start_time"], unique=False
    )

    # system_logs — 리소스 타입+ID 복합 인덱스 (감사 로그 조회 최적화)
    op.create_index(
        "ix_syslog_resource",
        "system_logs",
        ["resource_type", "resource_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_syslog_resource", table_name="system_logs")
    op.drop_index("ix_pr_start_time", table_name="process_results")
    op.drop_index("ix_pr_worker", table_name="process_results")
    op.drop_index("ix_wo_planned", table_name="work_orders")
    op.drop_index("ix_wo_process", table_name="work_orders")
    op.drop_index("ix_equipment_status", table_name="equipment")
    op.drop_index("ix_processes_type", table_name="processes")
    op.drop_index("ix_raw_materials_category", table_name="raw_materials")
    op.drop_index("ix_suppliers_grade", table_name="suppliers")
