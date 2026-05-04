// ============================================================
// 라우트 상수
// ============================================================

export const ROUTES = {
  LOGIN: '/login',
  DASHBOARD: '/',
  PROCESS: '/process',
  INVENTORY: '/inventory',
  /** 출하물류 — 설계 표준 경로: shipment/ (이전: logistics/) */
  SHIPMENT: '/shipment',
  /** 수주견적 AI — 설계 표준 경로: quotation/ (이전: orders/) */
  QUOTATION: '/quotation',
  MASTER_DATA: '/master-data',
  KPI: '/kpi',
  DATA_HUB: '/data-hub',
  AI_AGENT: '/ai-agent',
  /** 시스템관리 — 설계 표준 경로: system/ (이전: admin/) */
  SYSTEM: '/system',
} as const

export type RouteKey = keyof typeof ROUTES
export type RoutePath = (typeof ROUTES)[RouteKey]

// ============================================================
// 역할 상수 (DB: RBAC 5역할)
// ============================================================

export const ROLES = {
  PRODUCTION_MANAGER: 'production_manager',
  QUALITY_INSPECTOR: 'quality_inspector',
  PROCESS_ENGINEER: 'process_engineer',
  EXECUTIVE: 'executive',
  SALES_ENGINEER: 'sales_engineer',
  ADMIN: 'admin',
} as const

export type RoleValue = (typeof ROLES)[keyof typeof ROLES]

export const ROLE_LABELS: Record<RoleValue, string> = {
  production_manager: '생산 관리자',
  quality_inspector: '품질 검사원',
  process_engineer: '공정 엔지니어',
  executive: '경영진',
  sales_engineer: '영업 엔지니어',
  admin: '시스템 관리자',
}

// ============================================================
// LOT 상태 상수
// ============================================================

export const LOT_STATUS = {
  RECEIVED: 'received',
  IN_PROCESS: 'in_process',
  QUALITY_CHECK: 'quality_check',
  COMPLETED: 'completed',
  SHIPPED: 'shipped',
  ON_HOLD: 'on_hold',
  REJECTED: 'rejected',
} as const

export type LotStatusValue = (typeof LOT_STATUS)[keyof typeof LOT_STATUS]

export const LOT_STATUS_LABELS: Record<LotStatusValue, string> = {
  received: '입고 완료',
  in_process: '공정 중',
  quality_check: '품질 검사',
  completed: '완료',
  shipped: '출하 완료',
  on_hold: '보류',
  rejected: '불량',
}

export const LOT_STATUS_COLORS: Record<LotStatusValue, string> = {
  received: 'bg-blue-100 text-blue-800',
  in_process: 'bg-yellow-100 text-yellow-800',
  quality_check: 'bg-purple-100 text-purple-800',
  completed: 'bg-green-100 text-green-800',
  shipped: 'bg-gray-100 text-gray-800',
  on_hold: 'bg-orange-100 text-orange-800',
  rejected: 'bg-red-100 text-red-800',
}

// ============================================================
// 공정 타입 상수
// ============================================================

export const PROCESS_TYPES = {
  CUTTING: 'cutting',
  FORMING: 'forming',
  WELDING: 'welding',
  PAINTING: 'painting',
  INSPECTION: 'inspection',
} as const

export const PROCESS_TYPE_LABELS: Record<string, string> = {
  cutting: '절단',
  forming: '성형',
  welding: '용접',
  painting: '도장',
  inspection: '검사',
}

// ============================================================
// 설비 상태 상수
// ============================================================

export const EQUIPMENT_STATUS = {
  RUNNING: 'running',
  IDLE: 'idle',
  MAINTENANCE: 'maintenance',
  ERROR: 'error',
} as const

export const EQUIPMENT_STATUS_LABELS: Record<string, string> = {
  running: '가동 중',
  idle: '대기',
  maintenance: '점검 중',
  error: '오류',
}

export const EQUIPMENT_STATUS_COLORS: Record<string, string> = {
  running: 'bg-green-100 text-green-800',
  idle: 'bg-gray-100 text-gray-800',
  maintenance: 'bg-yellow-100 text-yellow-800',
  error: 'bg-red-100 text-red-800',
}

// ============================================================
// 수주 상태 상수
// ============================================================

export const ORDER_STATUS = {
  QUOTATION: 'quotation',
  CONFIRMED: 'confirmed',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
} as const

export const ORDER_STATUS_LABELS: Record<string, string> = {
  quotation: '견적',
  confirmed: '수주 확정',
  in_progress: '생산 중',
  completed: '완료',
  cancelled: '취소',
}

// ============================================================
// 페이지네이션 기본값
// ============================================================

export const DEFAULT_PAGE_SIZE = 20
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

// ============================================================
// AI Agent 타입 상수
// ============================================================

export const AGENT_TYPES = {
  INBOUND: 'inbound',
  OUTBOUND: 'outbound',
  INTEGRATED: 'integrated',
} as const

export const AGENT_TYPE_LABELS: Record<string, string> = {
  inbound: '공정/품질 인바운드',
  outbound: '견적/영업 아웃바운드',
  integrated: '통합 에이전트',
}

// ============================================================
// 로컬 스토리지 키
// ============================================================

export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'onetouch_access_token',
  REFRESH_TOKEN: 'onetouch_refresh_token',
  USER: 'onetouch_user',
  SIDEBAR_COLLAPSED: 'onetouch_sidebar_collapsed',
} as const
