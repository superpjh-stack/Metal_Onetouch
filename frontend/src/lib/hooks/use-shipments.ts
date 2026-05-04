import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'
import type { PaginatedResponse } from '@/types'

export interface ShipmentLot {
  id: string
  lot_id: string
  qty: number
  unit_price: number | null
  created_at: string
}

export interface Shipment {
  id: string
  shipment_number: string
  customer_id: string
  customer_name: string | null
  status: 'pending' | 'shipped' | 'delivered' | 'cancelled'
  planned_date: string | null
  shipped_date: string | null
  delivered_date: string | null
  notes: string | null
  lots: ShipmentLot[]
  created_at: string
  updated_at: string
}

export interface ShipmentCreate {
  customer_id: string
  planned_date?: string
  notes?: string
  lots?: Array<{ lot_id: string; qty: number; unit_price?: number }>
}

export interface ShipmentStatusUpdate {
  status: 'shipped' | 'delivered' | 'cancelled'
  notes?: string
}

export function useShipments(filters?: {
  status?: string
  customer_id?: string
  date_from?: string
  date_to?: string
  page?: number
  limit?: number
}) {
  return useQuery({
    queryKey: ['shipments', filters],
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<Shipment>>('/api/v1/shipments/', { params: filters })
        .then((r) => r.data),
  })
}

export function usePendingShipments() {
  return useQuery({
    queryKey: ['shipments-pending'],
    queryFn: () =>
      apiClient.get<Shipment[]>('/api/v1/shipments/pending').then((r) => r.data),
  })
}

export function useCreateShipment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ShipmentCreate) =>
      apiClient.post<Shipment>('/api/v1/shipments/', body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shipments'] })
      qc.invalidateQueries({ queryKey: ['lots'] })
    },
  })
}

export function useUpdateShipmentStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      shipmentId,
      body,
    }: {
      shipmentId: string
      body: ShipmentStatusUpdate
    }) =>
      apiClient
        .patch<Shipment>(`/api/v1/shipments/${shipmentId}/status`, body)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shipments'] })
      qc.invalidateQueries({ queryKey: ['lots'] })
    },
  })
}
