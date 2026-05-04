// ============================================================
// 공통 API 응답 타입
// ============================================================

export interface ApiResponse<T> {
  data: T
  meta?: {
    timestamp: string
    requestId?: string
  }
}

export interface PaginatedResponse<T> {
  data: T[]
  pagination: {
    page: number
    limit: number
    total: number
    totalPages: number
  }
  meta?: {
    timestamp: string
    requestId?: string
  }
}

export interface ErrorResponse {
  error: {
    code: string
    message: string
    details?: Array<{
      field: string
      message: string
    }>
  }
}

// ============================================================
// 인증 / 사용자 타입
// ============================================================

export type Role =
  | 'production_manager'
  | 'quality_inspector'
  | 'process_engineer'
  | 'executive'
  | 'sales_engineer'
  | 'admin'

export interface User {
  id: string
  email: string
  name: string
  role: Role
  department?: string
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface LoginInput {
  email: string
  password: string
}

export interface LoginResponse {
  user: User
  accessToken: string
  refreshToken: string
  expiresIn: number
}

// ============================================================
// LOT 타입 (DB: lots 테이블 기반)
// lot_id 형식: 'L{YYYYMMDD}-{SEQ}' (예: L20260430-001)
// ============================================================

export type LotStatus =
  | 'received'       // 입고 완료
  | 'in_process'     // 공정 중
  | 'quality_check'  // 품질 검사
  | 'completed'      // 완료
  | 'shipped'        // 출하 완료
  | 'on_hold'        // 보류
  | 'rejected'       // 불량 판정

export interface Lot {
  lotId: string
  orderId?: string
  itemCode: string
  itemName: string
  quantity: number
  unit: string
  status: LotStatus
  currentProcess?: string
  receivedAt: string
  completedAt?: string
  shippedAt?: string
  notes?: string
  createdAt: string
  updatedAt: string
}

export interface LotDetail extends Lot {
  history: LotHistory[]
  processData?: ProcessDataSummary[]
  qualityData?: QualityData[]
}

export interface LotHistory {
  id: string
  lotId: string
  action: string
  fromStatus?: LotStatus
  toStatus?: LotStatus
  processName?: string
  operatorId: string
  operatorName: string
  notes?: string
  createdAt: string
}

export interface LotListParams {
  page?: number
  limit?: number
  status?: LotStatus
  search?: string
  fromDate?: string
  toDate?: string
}

export interface LotCreateInput {
  orderId?: string
  itemCode: string
  itemName: string
  quantity: number
  unit: string
  notes?: string
}

export interface LotStatusUpdate {
  status: LotStatus
  processName?: string
  notes?: string
}

// ============================================================
// 공정 (Process) 타입
// ============================================================

export type ProcessType =
  | 'cutting'    // 절단
  | 'forming'    // 성형
  | 'welding'    // 용접
  | 'painting'   // 도장
  | 'inspection' // 검사

export interface Process {
  id: string
  name: string
  type: ProcessType
  sequenceNo: number
  description?: string
  standardTime?: number // 분 단위
  isActive: boolean
}

export interface ProcessDataSummary {
  processId: string
  processName: string
  startedAt: string
  completedAt?: string
  operatorName: string
  defectCount: number
  passCount: number
}

// ============================================================
// 품질 타입
// ============================================================

export type QualityResult = 'pass' | 'fail' | 'conditional'

export interface QualityData {
  id: string
  lotId: string
  processId: string
  inspectorId: string
  inspectorName: string
  result: QualityResult
  defectType?: string
  measuredValue?: number
  standardValue?: number
  notes?: string
  inspectedAt: string
}

// ============================================================
// 설비 / IoT 타입
// ============================================================

export type EquipmentStatus = 'running' | 'idle' | 'maintenance' | 'error'

export interface Equipment {
  id: string
  name: string
  code: string
  processId: string
  processName: string
  status: EquipmentStatus
  lastMaintenanceAt?: string
  nextMaintenanceAt?: string
}

export interface SensorData {
  equipmentId: string
  metricName: string
  value: number
  unit: string
  timestamp: string
}

// ============================================================
// KPI 타입
// ============================================================

export interface DashboardKpi {
  todayProduction: number
  defectRate: number          // 백분율 (%)
  equipmentUtilization: number // 백분율 (%)
  pendingShipments: number
  comparedToPrevDay: {
    production: number        // 전일 대비 변화율 (%)
    defectRate: number
    equipmentUtilization: number
    pendingShipments: number
  }
}

export interface ProductionTrend {
  date: string
  planned: number
  actual: number
  defects: number
}

// ============================================================
// 수주 / 견적 타입
// ============================================================

export type OrderStatus =
  | 'quotation'    // 견적
  | 'confirmed'    // 수주 확정
  | 'in_progress'  // 생산 중
  | 'completed'    // 완료
  | 'cancelled'    // 취소

export interface Order {
  id: string
  orderNo: string
  customerName: string
  itemName: string
  quantity: number
  unitPrice: number
  totalAmount: number
  status: OrderStatus
  deliveryDate: string
  notes?: string
  createdAt: string
}

// ============================================================
// 재고 타입
// ============================================================

export interface InventoryItem {
  id: string
  itemCode: string
  itemName: string
  category: string
  quantity: number
  unit: string
  warehouseLocation: string
  minQuantity: number
  maxQuantity: number
  lastUpdatedAt: string
}

// ============================================================
// AI Agent 타입
// ============================================================

export type AgentType = 'inbound' | 'outbound' | 'integrated'

export interface AgentMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  agentType?: AgentType
  metadata?: Record<string, unknown>
}

export interface AgentSession {
  id: string
  agentType: AgentType
  userId: string
  messages: AgentMessage[]
  createdAt: string
  updatedAt: string
}

// ============================================================
// 기준정보 (Master Data) 타입
// ============================================================

export interface Supplier {
  id: string
  supplier_code: string
  name: string
  contact_person?: string
  phone?: string
  email?: string
  grade: 'A' | 'B' | 'C' | 'D'
  business_no?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Customer {
  id: string
  customer_code: string
  name: string
  contact_person?: string
  phone?: string
  email?: string
  business_no?: string
  credit_limit?: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface RawMaterial {
  id: string
  material_code: string
  name: string
  category: string
  spec?: string
  unit: string
  supplier_id?: string
  supplier_name?: string
  stock_qty: number
  min_stock_qty: number
  unit_price?: number
  lead_time_days: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ProcessTypeRecord {
  id: string
  process_code: string
  name: string
  process_type: string
  std_time_min?: number
  description?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface EquipmentRecord {
  id: string
  equipment_code: string
  name: string
  process_id?: string
  process_name?: string
  manufacturer?: string
  model_no?: string
  status: 'running' | 'idle' | 'maintenance' | 'breakdown' | 'decommissioned'
  installed_at?: string
  next_maint_at?: string
  location?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// ============================================================
// 작업지시 / 공정실적 타입
// ============================================================

export interface WorkOrder {
  id: string
  wo_number: string
  lot_id: string
  lot_display_id?: string
  process_id: string
  process_name?: string
  equipment_id?: string
  equipment_name?: string
  assigned_to?: string
  assigned_name?: string
  status: 'pending' | 'in_progress' | 'completed' | 'on_hold' | 'cancelled'
  planned_start?: string
  planned_end?: string
  actual_start?: string
  actual_end?: string
  input_qty?: number
  output_qty?: number
  defect_qty: number
  notes?: string
  created_at: string
  updated_at: string
}

export interface ProcessResult {
  id: string
  work_order_id: string
  lot_id: string
  equipment_id?: string
  worker_id?: string
  worker_name?: string
  input_qty: number
  output_qty: number
  defect_qty: number
  start_time: string
  end_time: string
  condition_notes?: string
  defect_reason?: string
  created_at: string
}

// ============================================================
// 대시보드 요약 타입
// ============================================================

export interface DashboardSummary {
  today_production: number
  defect_rate: number
  equipment_utilization: number
  pending_shipments: number
  compared_to_prev_day: {
    production: number
    defect_rate: number
    equipment_utilization: number
    pending_shipments: number
  }
}
