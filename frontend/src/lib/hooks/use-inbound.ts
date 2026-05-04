import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'

export interface ReceiptRead {
  id: string
  receipt_number: string
  supplier_id: string
  supplier_name: string | null
  lot_id: string | null
  lot_display_id: string | null
  material_name: string
  material_code: string | null
  quantity: string
  unit: string
  unit_price: string | null
  received_date: string
  notes: string | null
  created_at: string
}

export interface ReceiptCreate {
  supplier_id: string
  material_name: string
  material_code?: string
  quantity: number
  unit: string
  unit_price?: number
  received_date: string
  notes?: string
}

export interface SupplierReceiptStats {
  supplier_id: string
  supplier_name: string
  total_receipts: number
  total_quantity: number
  avg_unit_price: number | null
  last_received_date: string | null
}

interface ReceiptsParams {
  supplier_id?: string
  date_from?: string
  date_to?: string
  limit?: number
  page?: number
}

export function useReceipts(params?: ReceiptsParams) {
  return useQuery({
    queryKey: ['receipts', params],
    queryFn: () =>
      apiClient
        .get<{ data: ReceiptRead[]; total: number }>('/api/v1/inbound', { params })
        .then((r) => r.data),
  })
}

export function useCreateReceipt() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ReceiptCreate) =>
      apiClient.post<ReceiptRead>('/api/v1/inbound', body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['receipts'] })
      qc.invalidateQueries({ queryKey: ['lots'] })
    },
  })
}

export function useSupplierStats(period_days = 30) {
  return useQuery({
    queryKey: ['inbound-supplier-stats', period_days],
    queryFn: () =>
      apiClient
        .get<SupplierReceiptStats[]>('/api/v1/inbound/stats/supplier', {
          params: { period_days },
        })
        .then((r) => r.data),
  })
}
