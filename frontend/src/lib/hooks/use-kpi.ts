import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'

export interface KpiSummary {
  production_rate: number
  defect_rate: number
  delivery_rate: number
  shipment_count: number
  targets: Record<string, number>
}

export interface KpiTrendItem {
  date: string
  value: number
}

export interface KpiProductionData {
  production_rate: number
  target: number | null
  trend: KpiTrendItem[]
}

export interface KpiQualityData {
  defect_rate: number
  target: number | null
  trend: KpiTrendItem[]
}

export interface KpiDeliveryData {
  delivery_rate: number
  target: number | null
  total_orders: number
  on_time_orders: number
}

export interface KpiShipmentData {
  shipment_count: number
  pending_count: number
  delivered_count: number
}

export interface KpiTargetUpsert {
  metric_key: string
  target_value: number
  unit?: string
  period?: string
}

export function useKpiSummary() {
  return useQuery({
    queryKey: ['kpi-summary'],
    queryFn: () =>
      apiClient.get<KpiSummary>('/api/v1/kpi/summary').then((r) => r.data),
    refetchInterval: 60_000,
  })
}

export function useKpiProductionTrend(days = 30) {
  return useQuery({
    queryKey: ['kpi-production', days],
    queryFn: () =>
      apiClient
        .get<KpiProductionData>('/api/v1/kpi/production', { params: { days } })
        .then((r) => r.data),
  })
}

export function useKpiQualityTrend(days = 30) {
  return useQuery({
    queryKey: ['kpi-quality', days],
    queryFn: () =>
      apiClient
        .get<KpiQualityData>('/api/v1/kpi/quality', { params: { days } })
        .then((r) => r.data),
  })
}

export function useKpiDelivery() {
  return useQuery({
    queryKey: ['kpi-delivery'],
    queryFn: () =>
      apiClient.get<KpiDeliveryData>('/api/v1/kpi/delivery').then((r) => r.data),
  })
}

export function useKpiShipment() {
  return useQuery({
    queryKey: ['kpi-shipment'],
    queryFn: () =>
      apiClient.get<KpiShipmentData>('/api/v1/kpi/shipment').then((r) => r.data),
  })
}

export function useUpdateKpiTargets() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (targets: KpiTargetUpsert[]) =>
      apiClient
        .put('/api/v1/kpi/targets', { targets })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['kpi-summary'] })
    },
  })
}
