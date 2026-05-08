import apiClient from './client'
import type { DashboardSummary } from '@/types'

// ============================================================
// 대시보드 API 함수들
// ============================================================

export const dashboardApi = {
  /**
   * 대시보드 KPI 요약 조회
   * GET /api/v1/dashboard/summary
   */
  getSummary: () =>
    apiClient
      .get<DashboardSummary>('/api/v1/dashboard/summary')
      .then((r) => r.data),

  /**
   * 생산 추이 조회 (최근 N일)
   * GET /api/v1/dashboard/production-trend
   */
  getProductionTrend: (days = 7) =>
    apiClient
      .get<Array<{
        date: string
        planned: number
        actual: number
        defects: number
      }>>('/api/v1/dashboard/production-trend', { params: { days } })
      .then((r) => r.data),

  /**
   * 오늘의 LOT 현황
   * GET /api/v1/dashboard/lot-status
   */
  getLotStatus: () =>
    apiClient
      .get<Array<{
        lot_id: string
        item: string
        status: string
        process: string
        operator: string
      }>>('/api/v1/dashboard/lot-status')
      .then((r) => r.data),
}
