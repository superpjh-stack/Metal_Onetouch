import apiClient from './client'
import type {
  Lot,
  LotDetail,
  LotListParams,
  LotCreateInput,
  LotStatusUpdate,
  PaginatedResponse,
  ApiResponse,
} from '@/types'

// ============================================================
// LOT API 함수들
// lot_id 형식: 'L{YYYYMMDD}-{SEQ}' (예: L20260430-001)
// lots 테이블: DELETE 금지 (DB RULE)
// ============================================================

export const lotsApi = {
  /**
   * LOT 목록 조회 (페이지네이션)
   * GET /api/v1/lots
   */
  getList: (params?: LotListParams) =>
    apiClient.get<PaginatedResponse<Lot>>('/api/v1/lots', { params }),

  /**
   * LOT 상세 조회
   * GET /api/v1/lots/:lotId
   */
  getById: (lotId: string) =>
    apiClient.get<ApiResponse<LotDetail>>(`/api/v1/lots/${lotId}`),

  /**
   * LOT 생성 (입고 등록)
   * POST /api/v1/lots
   */
  create: (data: LotCreateInput) =>
    apiClient.post<ApiResponse<LotDetail>>('/api/v1/lots', data),

  /**
   * LOT 상태 변경
   * PATCH /api/v1/lots/:lotId/status
   * 주의: DELETE는 DB 레벨에서 금지됨
   */
  updateStatus: (lotId: string, data: LotStatusUpdate) =>
    apiClient.patch<ApiResponse<LotDetail>>(`/api/v1/lots/${lotId}/status`, data),

  /**
   * LOT 이력 조회
   * GET /api/v1/lots/:lotId/history
   */
  getHistory: (lotId: string) =>
    apiClient.get<ApiResponse<LotDetail['history']>>(`/api/v1/lots/${lotId}/history`),

  /**
   * LOT 추적성 조회 (전 공정 흐름)
   * GET /api/v1/lots/:lotId/traceability
   */
  getTraceability: (lotId: string) =>
    apiClient.get<ApiResponse<LotDetail>>(`/api/v1/lots/${lotId}/traceability`),

  /**
   * LOT 노트 수정
   * PATCH /api/v1/lots/:lotId/notes
   */
  updateNotes: (lotId: string, notes: string) =>
    apiClient.patch<ApiResponse<Lot>>(`/api/v1/lots/${lotId}/notes`, { notes }),
}
