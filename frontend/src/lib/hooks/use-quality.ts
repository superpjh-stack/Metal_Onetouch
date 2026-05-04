import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'
import type { PaginatedResponse } from '@/types'

export interface QualityInspection {
  id: string
  lot_id: string
  inspector_id: string | null
  inspection_type: string
  result: 'pass' | 'fail' | 'conditional'
  defect_rate: number
  inspection_date: string
  notes: string | null
  defects: DefectDetail[]
  created_at: string
}

export interface DefectDetail {
  id: string
  inspection_id: string
  defect_code: string
  defect_type: string
  qty: number
  description: string | null
  root_cause: string | null
  created_at: string
}

export interface QualityInspectionCreate {
  lot_id: string
  inspection_type: 'incoming' | 'in_process' | 'final' | 'shipment'
  result: 'pass' | 'fail' | 'conditional'
  defect_rate?: number
  inspection_date?: string
  notes?: string
  defects?: Omit<DefectDetail, 'id' | 'inspection_id' | 'created_at'>[]
}

export interface DefectStatsResponse {
  group_by: string
  period_days: number
  items: Array<{
    group_key: string
    group_label: string
    total_inspections: number
    fail_count: number
    avg_defect_rate: number
  }>
}

export function useQualityInspections(filters?: {
  lot_id?: string
  result?: string
  inspection_type?: string
  page?: number
  limit?: number
}) {
  return useQuery({
    queryKey: ['quality-inspections', filters],
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<QualityInspection>>('/api/v1/quality/', { params: filters })
        .then((r) => r.data),
  })
}

export function useLotInspections(lotId: string | undefined) {
  return useQuery({
    queryKey: ['lot-inspections', lotId],
    queryFn: () =>
      apiClient
        .get<QualityInspection[]>(`/api/v1/quality/lot/${lotId}`)
        .then((r) => r.data),
    enabled: !!lotId,
  })
}

export function useDefectStats(params?: { group_by?: string; period_days?: number }) {
  return useQuery({
    queryKey: ['defect-stats', params],
    queryFn: () =>
      apiClient
        .get<DefectStatsResponse>('/api/v1/quality/stats', { params })
        .then((r) => r.data),
  })
}

export function useCreateInspection() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: QualityInspectionCreate) =>
      apiClient.post<QualityInspection>('/api/v1/quality/', body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['quality-inspections'] })
      qc.invalidateQueries({ queryKey: ['lots'] })
    },
  })
}
