'use client'

import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import {
  Factory,
  AlertTriangle,
  Cpu,
  Truck,
  RefreshCw,
  Activity,
} from 'lucide-react'
import { KpiCard } from '@/components/ui/kpi-card'
import { Skeleton } from '@/components/ui/skeleton'
import { useUiStore } from '@/lib/stores/ui-store'
import {
  useDashboardSummary,
  useProductionTrend,
  useLotStatus,
} from '@/lib/hooks/use-dashboard'
import { formatDateTime } from '@/lib/utils/format'

// ============================================================
// AI 대시보드 홈 페이지 (React Query 연동)
// ============================================================

export default function DashboardPage() {
  const { setPageTitle } = useUiStore()
  const queryClient = useQueryClient()

  const { data: summary, isLoading: summaryLoading } = useDashboardSummary()
  const { data: trend, isLoading: trendLoading } = useProductionTrend(7)
  const { data: lotStatus, isLoading: lotLoading } = useLotStatus()

  useEffect(() => {
    setPageTitle('AI 대시보드')
  }, [setPageTitle])

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }

  return (
    <div className="space-y-6">
      {/* 페이지 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">AI 대시보드</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">
            금속 가공 생산 현황 실시간 모니터링
          </p>
        </div>

        {/* 실시간 상태 + 갱신 */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 dark:bg-green-950/40">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
            </span>
            <Activity className="h-3.5 w-3.5 text-green-600 dark:text-green-400" />
            <span className="text-xs font-medium text-green-700 dark:text-green-400">
              실시간 업데이트 중
            </span>
          </div>

          <button
            onClick={handleRefresh}
            className="flex items-center gap-1.5 rounded-lg border bg-card px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            수동 갱신
          </button>

          <span className="text-xs text-muted-foreground">
            {formatDateTime(new Date())} 기준
          </span>
        </div>
      </div>

      {/* KPI 카드 4개 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {summaryLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))
        ) : (
          <>
            <KpiCard
              title="오늘 생산량"
              value={summary?.today_production ?? 0}
              unit="개"
              change={summary?.compared_to_prev_day.production}
              status="normal"
              icon={Factory}
              description="목표 대비 현황"
            />
            <KpiCard
              title="불량률"
              value={summary?.defect_rate ?? 0}
              unit="%"
              change={summary?.compared_to_prev_day.defect_rate}
              changeInverse={true}
              status={
                (summary?.defect_rate ?? 0) > 3
                  ? 'critical'
                  : (summary?.defect_rate ?? 0) > 2
                  ? 'warning'
                  : 'normal'
              }
              icon={AlertTriangle}
              description="기준치 3.0% 이하"
            />
            <KpiCard
              title="설비 가동률"
              value={summary?.equipment_utilization ?? 0}
              unit="%"
              change={summary?.compared_to_prev_day.equipment_utilization}
              status={
                (summary?.equipment_utilization ?? 0) < 80
                  ? 'critical'
                  : (summary?.equipment_utilization ?? 0) < 90
                  ? 'warning'
                  : 'normal'
              }
              icon={Cpu}
              description="전체 설비 가동률"
            />
            <KpiCard
              title="출하 대기"
              value={summary?.pending_shipments ?? 0}
              unit="건"
              change={summary?.compared_to_prev_day.pending_shipments}
              changeInverse={true}
              status={
                (summary?.pending_shipments ?? 0) > 30 ? 'warning' : 'normal'
              }
              icon={Truck}
              description="오늘 출하 대기 현황"
            />
          </>
        )}
      </div>

      {/* 생산 추이 차트 + LOT 현황 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* 생산 추이 AreaChart */}
        <div className="rounded-xl border bg-card p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-foreground">
                7일 생산 추이
              </h3>
              <p className="text-xs text-muted-foreground">
                계획 대비 실적 및 불량 현황
              </p>
            </div>
          </div>

          {trendLoading ? (
            <Skeleton className="h-60 w-full" />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart
                data={trend ?? []}
                margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="colorPlanned" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#94a3b8" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="hsl(var(--border))"
                />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                  formatter={(value: number, name: string) => [
                    `${value.toLocaleString('ko-KR')}개`,
                    name === 'planned'
                      ? '계획'
                      : name === 'actual'
                      ? '실적'
                      : '불량',
                  ]}
                />
                <Legend
                  formatter={(value) =>
                    value === 'planned'
                      ? '계획'
                      : value === 'actual'
                      ? '실적'
                      : '불량'
                  }
                  wrapperStyle={{ fontSize: '12px' }}
                />
                <Area
                  type="monotone"
                  dataKey="planned"
                  stroke="#94a3b8"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  fill="url(#colorPlanned)"
                />
                <Area
                  type="monotone"
                  dataKey="actual"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  fill="url(#colorActual)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* 최근 LOT 현황 */}
        <div className="rounded-xl border bg-card p-5">
          <div className="mb-4">
            <h3 className="text-base font-semibold text-foreground">
              오늘의 LOT 현황
            </h3>
            <p className="text-xs text-muted-foreground">최근 5개 LOT</p>
          </div>

          {lotLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-20 rounded-lg" />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {(lotStatus ?? []).map((lot) => (
                <div
                  key={lot.lot_id}
                  className="flex items-start gap-3 rounded-lg border p-3 hover:bg-accent/50 transition-colors cursor-pointer"
                >
                  <div className="mt-0.5 flex-1 min-w-0">
                    <p className="text-xs font-mono font-medium text-primary">
                      {lot.lot_id}
                    </p>
                    <p className="mt-0.5 text-sm font-medium text-foreground truncate">
                      {lot.item}
                    </p>
                    <div className="mt-1 flex items-center gap-2">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${getStatusStyle(lot.status)}`}
                      >
                        {lot.status}
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        {lot.process}
                      </span>
                    </div>
                  </div>
                  <p className="shrink-0 text-xs text-muted-foreground">
                    {lot.operator}
                  </p>
                </div>
              ))}
            </div>
          )}

          <button className="mt-4 w-full rounded-lg border py-2 text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
            전체 LOT 보기
          </button>
        </div>
      </div>
    </div>
  )
}

// ============================================================
// LOT 상태 뱃지 색상 헬퍼
// ============================================================

function getStatusStyle(status: string): string {
  const map: Record<string, string> = {
    '입고 완료': 'bg-blue-100 text-blue-700 dark:bg-blue-950/50 dark:text-blue-400',
    '공정 중': 'bg-yellow-100 text-yellow-700 dark:bg-yellow-950/50 dark:text-yellow-400',
    '품질 검사': 'bg-purple-100 text-purple-700 dark:bg-purple-950/50 dark:text-purple-400',
    '출하 대기': 'bg-orange-100 text-orange-700 dark:bg-orange-950/50 dark:text-orange-400',
    '완료': 'bg-green-100 text-green-700 dark:bg-green-950/50 dark:text-green-400',
    '보류': 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
    '불량': 'bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-400',
  }
  return map[status] ?? 'bg-gray-100 text-gray-700'
}
