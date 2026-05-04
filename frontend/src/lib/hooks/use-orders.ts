import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'

export interface OrderItemRead {
  id: string
  material_name: string
  material_code: string | null
  quantity: string
  unit: string
  unit_price: string | null
  lot_id: string | null
}

export interface OrderRead {
  id: string
  order_number: string
  customer_id: string
  customer_name: string | null
  status: string
  ordered_date: string
  due_date: string | null
  total_amount: string | null
  items: OrderItemRead[]
  created_at: string
  updated_at: string
}

export interface OrderItemCreate {
  material_name: string
  material_code?: string
  quantity: number
  unit: string
  unit_price?: number
}

export interface OrderCreate {
  customer_id: string
  ordered_date: string
  due_date?: string
  notes?: string
  items: OrderItemCreate[]
}

interface OrdersParams {
  status?: string
  customer_id?: string
  date_from?: string
  date_to?: string
  page?: number
  limit?: number
}

export function useOrders(params?: OrdersParams) {
  return useQuery({
    queryKey: ['orders', params],
    queryFn: () =>
      apiClient
        .get<{ data: OrderRead[]; total: number }>('/api/v1/orders', { params })
        .then((r) => r.data),
  })
}

export function useCreateOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: OrderCreate) =>
      apiClient.post<OrderRead>('/api/v1/orders', body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['orders'] })
    },
  })
}

export function useUpdateOrderStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiClient
        .patch<OrderRead>(`/api/v1/orders/${id}/status`, { status })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['orders'] })
    },
  })
}
