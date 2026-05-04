import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { workOrdersApi } from '@/lib/api/work-orders'

// ============================================================
// 작업지시 React Query 훅
// ============================================================

export function useWorkOrders(
  params?: Parameters<typeof workOrdersApi.list>[0]
) {
  return useQuery({
    queryKey: ['work-orders', params],
    queryFn: () => workOrdersApi.list(params),
    staleTime: 30_000,
  })
}

export function useWorkOrder(id: string) {
  return useQuery({
    queryKey: ['work-orders', id],
    queryFn: () => workOrdersApi.get(id),
    enabled: !!id,
  })
}

export function useCreateWorkOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: workOrdersApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['work-orders'] }),
  })
}

export function useUpdateWorkOrderStatus() {
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
    }) => workOrdersApi.updateStatus(id, status, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['work-orders'] }),
  })
}

export function useAddProcessResult(workOrderId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Parameters<typeof workOrdersApi.addResult>[1]) =>
      workOrdersApi.addResult(workOrderId, body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['work-orders', workOrderId] }),
  })
}
