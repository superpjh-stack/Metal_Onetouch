import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  suppliersApi,
  customersApi,
  materialsApi,
  processTypesApi,
  equipmentApi,
  type ListParams,
} from '@/lib/api/master'

// ============================================================
// 공급업체 (Suppliers)
// ============================================================

export function useSuppliers(
  params?: ListParams & { grade?: string }
) {
  return useQuery({
    queryKey: ['suppliers', params],
    queryFn: () => suppliersApi.list(params),
    staleTime: 5 * 60_000,
  })
}

export function useCreateSupplier() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: suppliersApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['suppliers'] }),
  })
}

export function useUpdateSupplier() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string
      body: Parameters<typeof suppliersApi.update>[1]
    }) => suppliersApi.update(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['suppliers'] }),
  })
}

// ============================================================
// 고객사 (Customers)
// ============================================================

export function useCustomers(params?: ListParams) {
  return useQuery({
    queryKey: ['customers', params],
    queryFn: () => customersApi.list(params),
    staleTime: 5 * 60_000,
  })
}

export function useCreateCustomer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: customersApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['customers'] }),
  })
}

export function useUpdateCustomer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string
      body: Parameters<typeof customersApi.update>[1]
    }) => customersApi.update(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['customers'] }),
  })
}

// ============================================================
// 원자재 (Materials)
// ============================================================

export function useMaterials(
  params?: ListParams & { category?: string; supplier_id?: string }
) {
  return useQuery({
    queryKey: ['materials', params],
    queryFn: () => materialsApi.list(params),
    staleTime: 5 * 60_000,
  })
}

export function useCreateMaterial() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: materialsApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['materials'] }),
  })
}

// ============================================================
// 설비 (Equipment)
// ============================================================

export function useEquipment(
  params?: ListParams & { status?: string; process_id?: string }
) {
  return useQuery({
    queryKey: ['equipment', params],
    queryFn: () => equipmentApi.list(params),
    staleTime: 5 * 60_000,
  })
}

export function useUpdateEquipmentStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      status,
      reason,
    }: {
      id: string
      status: string
      reason?: string
    }) => equipmentApi.updateStatus(id, status, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['equipment'] }),
  })
}

export function useCreateEquipment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: equipmentApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['equipment'] }),
  })
}

// ============================================================
// 공정유형 (Process Types)
// ============================================================

export function useProcessTypes(
  params?: ListParams & { process_type?: string }
) {
  return useQuery({
    queryKey: ['process-types', params],
    queryFn: () => processTypesApi.list(params),
    staleTime: 10 * 60_000,
  })
}

export function useCreateProcessType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: processTypesApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['process-types'] }),
  })
}
