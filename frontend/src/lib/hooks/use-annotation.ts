import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'

export interface AnnotationTaskRead {
  id: string
  drawing_id: string
  status: 'pending' | 'in_progress' | 'completed' | 'skipped'
  original_parsed: Record<string, unknown>
  corrected_parsed: Record<string, unknown> | null
  annotator_id: string | null
  assigned_at: string | null
  completed_at: string | null
  skip_reason: string | null
  created_at: string
}

export function useAnnotationTask(drawingId: string | undefined) {
  return useQuery<AnnotationTaskRead | null>({
    queryKey: ['annotation-task', drawingId],
    queryFn: () =>
      apiClient.get(`/cad/${drawingId}/annotation-task`).then((r) => r.data),
    enabled: !!drawingId,
  })
}

export function useAnnotationTasks(params?: {
  status?: string
  page?: number
  limit?: number
}) {
  return useQuery({
    queryKey: ['annotation-tasks', params],
    queryFn: () =>
      apiClient
        .get('/ml/annotation-tasks', { params })
        .then((r) => r.data as { data: AnnotationTaskRead[]; total: number }),
  })
}

export function useSubmitAnnotation(drawingId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (corrected_parsed: Record<string, unknown>) =>
      apiClient
        .put(`/cad/${drawingId}/annotation`, { corrected_parsed })
        .then((r) => r.data as AnnotationTaskRead),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['annotation-task', drawingId] })
      qc.invalidateQueries({ queryKey: ['annotation-tasks'] })
      qc.invalidateQueries({ queryKey: ['drawing', drawingId] })
    },
  })
}
