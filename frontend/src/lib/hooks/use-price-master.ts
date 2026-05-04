import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'

export interface ProcessPriceRead {
  id: string
  process_type: string
  material_grade: string | null
  unit_price: string
  price_unit: string
  effective_from: string
  notes: string | null
}

export interface MaterialPriceRead {
  id: string
  material_code: string
  material_name: string
  price_per_kg: string
  density: string
  notes: string | null
}

export interface ProcessPriceUpsert {
  process_type: string
  material_grade?: string
  unit_price: number
  price_unit: string
  notes?: string
}

export interface MaterialPriceUpsert {
  material_code: string
  material_name: string
  price_per_kg: number
  density: number
  notes?: string
}

export function useProcessPrices() {
  return useQuery({
    queryKey: ['process-prices'],
    queryFn: () =>
      apiClient.get<ProcessPriceRead[]>('/api/v1/master/process-prices').then((r) => r.data),
  })
}

export function useUpsertProcessPrices() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (items: ProcessPriceUpsert[]) =>
      apiClient
        .put<ProcessPriceRead[]>('/api/v1/master/process-prices', items)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['process-prices'] })
    },
  })
}

export function useMaterialPrices() {
  return useQuery({
    queryKey: ['material-prices'],
    queryFn: () =>
      apiClient.get<MaterialPriceRead[]>('/api/v1/master/material-prices').then((r) => r.data),
  })
}

export function useUpsertMaterialPrices() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (items: MaterialPriceUpsert[]) =>
      apiClient
        .put<MaterialPriceRead[]>('/api/v1/master/material-prices', items)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['material-prices'] })
    },
  })
}
