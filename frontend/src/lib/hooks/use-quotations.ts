import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'

export interface QuotationItemRead {
  id: string
  item_type: string
  description: string | null
  quantity: string
  unit: string | null
  unit_price: string
  amount: string
  sort_order: number
}

export interface QuotationRead {
  id: string
  quotation_number: string
  customer_id: string
  customer_name: string | null
  drawing_id: string | null
  order_id: string | null
  status: 'draft' | 'submitted' | 'accepted' | 'rejected' | 'expired'
  material_cost: string
  process_cost: string
  total_amount: string
  margin_rate: string
  final_amount: string
  valid_until: string | null
  version: number
  notes: string | null
  items: QuotationItemRead[]
  created_at: string
  updated_at: string
}

export interface QuotationSummary {
  id: string
  quotation_number: string
  customer_name: string | null
  final_amount: string
  total_amount: string
  status: string
  created_at: string
}

export interface QuotationCreate {
  customer_id: string
  drawing_id?: string
  material_code?: string
  margin_rate?: number
  notes?: string
}

export interface QuotationItemUpdate {
  id: string
  unit_price: string
  quantity?: string
  description?: string
}

interface QuotationsParams {
  customer_id?: string
  status?: string
  page?: number
  limit?: number
}

export function useQuotations(params?: QuotationsParams) {
  return useQuery({
    queryKey: ['quotations', params],
    queryFn: () =>
      apiClient
        .get<{ data: QuotationSummary[]; total: number }>('/api/v1/quotations', { params })
        .then((r) => r.data),
  })
}

export function useQuotation(quotationId: string | null) {
  return useQuery({
    queryKey: ['quotations', quotationId],
    queryFn: () =>
      apiClient.get<QuotationRead>(`/api/v1/quotations/${quotationId}`).then((r) => r.data),
    enabled: !!quotationId,
  })
}

export function useSimilarQuotations(quotationId: string | null, topK = 5) {
  return useQuery({
    queryKey: ['quotations-similar', quotationId],
    queryFn: () =>
      apiClient
        .get<QuotationSummary[]>(`/api/v1/quotations/${quotationId}/similar`, {
          params: { top_k: topK },
        })
        .then((r) => r.data),
    enabled: !!quotationId,
  })
}

export function useCreateQuotation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: QuotationCreate) =>
      apiClient.post<QuotationRead>('/api/v1/quotations', body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['quotations'] })
    },
  })
}

export function useUpdateQuotationItems() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, items }: { id: string; items: QuotationItemUpdate[] }) =>
      apiClient
        .patch<QuotationRead>(`/api/v1/quotations/${id}/items`, items)
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['quotations', vars.id] })
      qc.invalidateQueries({ queryKey: ['quotations'] })
    },
  })
}

export function useSubmitQuotation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.post<QuotationRead>(`/api/v1/quotations/${id}/submit`).then((r) => r.data),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['quotations', id] })
      qc.invalidateQueries({ queryKey: ['quotations'] })
    },
  })
}

export function useLinkQuotationOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, order_id }: { id: string; order_id: string }) =>
      apiClient
        .patch<QuotationRead>(`/api/v1/quotations/${id}/link-order`, { order_id })
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['quotations', vars.id] })
    },
  })
}
