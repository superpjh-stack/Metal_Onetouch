import apiClient from './client'
import type { WorkOrder, ProcessResult, PaginatedResponse } from '@/types'

// ============================================================
// 작업지시 API 함수들
// ============================================================

export const workOrdersApi = {
  list: (params?: {
    page?: number
    limit?: number
    status?: string
    lot_id?: string
  }) =>
    apiClient
      .get<PaginatedResponse<WorkOrder>>('/api/v1/work-orders', { params })
      .then((r) => r.data),

  get: (id: string) =>
    apiClient
      .get<{ data: WorkOrder & { process_results: ProcessResult[] } }>(
        `/api/v1/work-orders/${id}`
      )
      .then((r) => r.data.data),

  create: (body: Partial<WorkOrder>) =>
    apiClient
      .post<WorkOrder>('/api/v1/work-orders', body)
      .then((r) => r.data),

  updateStatus: (id: string, status: string, reason?: string) =>
    apiClient
      .patch<WorkOrder>(`/api/v1/work-orders/${id}/status`, { status, reason })
      .then((r) => r.data),

  addResult: (id: string, body: Partial<ProcessResult>) =>
    apiClient
      .post<ProcessResult>(`/api/v1/work-orders/${id}/results`, body)
      .then((r) => r.data),

  getResults: (id: string) =>
    apiClient
      .get<PaginatedResponse<ProcessResult>>(
        `/api/v1/work-orders/${id}/results`
      )
      .then((r) => r.data),
}
