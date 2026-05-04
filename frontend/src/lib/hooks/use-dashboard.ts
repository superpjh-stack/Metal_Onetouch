import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '@/lib/api/dashboard'

// ============================================================
// 대시보드 React Query 훅
// ============================================================

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: dashboardApi.getSummary,
    staleTime: 30_000,
    refetchInterval: 30_000,
  })
}

export function useProductionTrend(days = 7) {
  return useQuery({
    queryKey: ['dashboard', 'production-trend', days],
    queryFn: () => dashboardApi.getProductionTrend(days),
    staleTime: 60_000,
  })
}

export function useLotStatus() {
  return useQuery({
    queryKey: ['dashboard', 'lot-status'],
    queryFn: dashboardApi.getLotStatus,
    staleTime: 30_000,
    refetchInterval: 30_000,
  })
}
