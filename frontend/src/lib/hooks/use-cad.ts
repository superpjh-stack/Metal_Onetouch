import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'

export interface CadObjectItem {
  type: 'hole' | 'slot' | 'bend' | 'cut' | 'weld'
  count: number
  diameter?: number
  width?: number
  length?: number
  angle?: number
  radius?: number
  tolerance?: string
}

export interface CadDimensions {
  length: number
  width: number
  thickness: number
}

export interface CadDrawingRead {
  id: string
  drawing_number: string
  file_id: string
  customer_id: string | null
  analysis_status: 'pending' | 'analyzing' | 'completed' | 'failed'
  parsed_objects: { objects: CadObjectItem[] } | null
  dimensions: CadDimensions | null
  material_hint: string | null
  confidence: number | null
  analyzed_at: string | null
  error_message: string | null
  notes: string | null
  created_at: string
}

export interface CadStatusResponse {
  id: string
  drawing_number: string
  analysis_status: 'pending' | 'analyzing' | 'completed' | 'failed'
  analyzed_at: string | null
  error_message: string | null
}

export interface CadDrawingCreate {
  file_id: string
  customer_id?: string
  notes?: string
}

export interface CadUpdateObjects {
  objects: CadObjectItem[]
  dimensions: CadDimensions
}

interface DrawingsParams {
  analysis_status?: string
  customer_id?: string
  page?: number
  limit?: number
}

export function useDrawings(params?: DrawingsParams) {
  return useQuery({
    queryKey: ['cad-drawings', params],
    queryFn: () =>
      apiClient
        .get<{ data: CadDrawingRead[]; total: number }>('/api/v1/cad', { params })
        .then((r) => r.data),
  })
}

export function useDrawing(drawingId: string | null) {
  return useQuery({
    queryKey: ['cad-drawings', drawingId],
    queryFn: () =>
      apiClient.get<CadDrawingRead>(`/api/v1/cad/${drawingId}`).then((r) => r.data),
    enabled: !!drawingId,
  })
}

/** Polls every 3 s until analysis completes or fails */
export function useDrawingStatus(drawingId: string | null) {
  return useQuery({
    queryKey: ['cad-status', drawingId],
    queryFn: () =>
      apiClient
        .get<CadStatusResponse>(`/api/v1/cad/${drawingId}/status`)
        .then((r) => r.data),
    enabled: !!drawingId,
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return 3000
      return data.analysis_status === 'completed' || data.analysis_status === 'failed'
        ? false
        : 3000
    },
  })
}

export function useCreateDrawing() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CadDrawingCreate) =>
      apiClient.post<CadDrawingRead>('/api/v1/cad', body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cad-drawings'] })
    },
  })
}

export function useUpdateDrawingObjects() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & CadUpdateObjects) =>
      apiClient
        .patch<CadDrawingRead>(`/api/v1/cad/${id}/objects`, body)
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['cad-drawings', vars.id] })
    },
  })
}
