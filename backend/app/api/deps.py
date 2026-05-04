"""
공통 FastAPI Depends 모음
"""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.user import User

# -------------------------------------------------------------------
# DB 세션
# -------------------------------------------------------------------
DBSession = Annotated[AsyncSession, Depends(get_db)]

# -------------------------------------------------------------------
# 인증된 현재 사용자
# -------------------------------------------------------------------
CurrentUser = Annotated[User, Depends(get_current_user)]

# -------------------------------------------------------------------
# 역할별 접근 제어 Depends (재사용 가능한 인스턴스)
# -------------------------------------------------------------------

# 생산 관리자 이상 (생산 데이터 쓰기)
require_production_manager = require_roles("production_manager", "executive", "admin")

# 품질 검사자 이상
require_quality_inspector = require_roles(
    "quality_inspector", "production_manager", "executive", "admin"
)

# 공정 엔지니어 이상
require_process_engineer = require_roles(
    "process_engineer", "production_manager", "executive", "admin"
)

# 임원 전용 (읽기 전용 대시보드, 경영 보고서)
require_executive = require_roles("executive", "admin")

# 영업 엔지니어 이상
require_sales_engineer = require_roles(
    "sales_engineer", "production_manager", "executive", "admin"
)

# 관리자 전용
require_admin = require_roles("admin")

# 모든 인증된 사용자 (읽기)
require_any_role = require_roles(
    "production_manager",
    "quality_inspector",
    "process_engineer",
    "executive",
    "sales_engineer",
    "admin",
)
