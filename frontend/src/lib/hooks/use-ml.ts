import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'

export interface AnnotationDatasetRead {
  id: string
  version: string
  image_count: number
  label_counts: Record<string, number>
  s3_path: string | null
  status: 'building' | 'ready' | 'failed'
  built_at: string | null
  notes: string | null
  created_at: string
}

export interface TrainingJobCreate {
  dataset_id: string
  model_version?: string
  epochs?: number
  batch_size?: number
  img_size?: number
  hyperparams?: Record<string, unknown>
}

export interface TrainingJobRead {
  id: string
  dataset_id: string
  model_version: string
  epochs: number
  batch_size: number
  img_size: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  train_map50: number | null
  val_map50: number | null
  model_s3_path: string | null
  mlflow_run_id: string | null
  is_active: boolean
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  hyperparams: Record<string, unknown>
  created_at: string
}

export function useDatasets(params?: { page?: number; limit?: number }) {
  return useQuery({
    queryKey: ['annotation-datasets', params],
    queryFn: () =>
      apiClient
        .get('/ml/datasets', { params })
        .then((r) => r.data as { data: AnnotationDatasetRead[]; total: number }),
  })
}

export function useBuildDataset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (notes?: string) =>
      apiClient.post('/ml/datasets/build', { notes }).then((r) => r.data as AnnotationDatasetRead),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['annotation-datasets'] }),
  })
}

export function useTrainingJobs(params?: { status?: string; page?: number; limit?: number }) {
  return useQuery({
    queryKey: ['training-jobs', params],
    queryFn: () =>
      apiClient
        .get('/ml/training-jobs', { params })
        .then((r) => r.data as { data: TrainingJobRead[]; total: number }),
  })
}

export function useTrainingJobStatus(jobId: string | undefined) {
  return useQuery({
    queryKey: ['training-job', jobId],
    queryFn: () =>
      apiClient.get(`/ml/training-jobs/${jobId}`).then((r) => r.data as TrainingJobRead),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const s = query.state.data?.status
      return s === 'running' || s === 'pending' ? 10000 : false
    },
  })
}

export function useStartTraining() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TrainingJobCreate) =>
      apiClient.post('/ml/training-jobs', data).then((r) => r.data as TrainingJobRead),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['training-jobs'] }),
  })
}

export function useActivateModel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) =>
      apiClient
        .patch(`/ml/training-jobs/${jobId}/activate`)
        .then((r) => r.data as TrainingJobRead),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['training-jobs'] }),
  })
}
