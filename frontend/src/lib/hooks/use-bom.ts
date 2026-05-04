import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'

export interface BomItemRead {
  id: string
  material_code: string
  specification: string
  quantity: number
  unit: string
  unit_weight_kg: number | null
  total_weight_kg: number
  sort_order: number
}

export interface BomRead {
  id: string
  quotation_id: string
  order_id: string | null
  revision: number
  total_weight_kg: number
  notes: string | null
  items: BomItemRead[]
  created_at: string
  updated_at: string
}

export function useBom(quotationId: string | undefined) {
  return useQuery<BomRead | null>({
    queryKey: ['bom', quotationId],
    queryFn: () =>
      apiClient.get(`/quotations/${quotationId}/bom`).then((r) => r.data),
    enabled: !!quotationId,
  })
}

export function useGenerateBom(quotationId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiClient.post(`/quotations/${quotationId}/bom`).then((r) => r.data as BomRead),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bom', quotationId] }),
  })
}

export function useExportBom() {
  return useMutation({
    mutationFn: async (bomId: string) => {
      const response = await apiClient.get(`/bom/${bomId}/export`, {
        responseType: 'blob',
      })
      const url = URL.createObjectURL(response.data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `bom-${bomId}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    },
  })
}
