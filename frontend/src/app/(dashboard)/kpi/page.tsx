'use client'

import { useEffect } from 'react'
import { useUiStore } from '@/lib/stores/ui-store'
import { PageHeader } from '@/components/ui/page-header'
import { KpiCard } from '@/components/ui/kpi-card'
import {
  useKpiSummary,
  useKpiProductionTrend,
  useKpiQualityTrend,
  useKpiDelivery,
  useKpiShipment,
} from '@/lib/hooks/use-kpi'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'

export default function KpiPage() {
  const { setPageTitle } = useUiStore()
  useEffect(() => { setPageTitle('KPI 관리') }, [setPageTitle])

  const { data: summary } = useKpiSummary()
  const { data: prodData } = useKpiProductionTrend(30)
  const { data: qualData } = useKpiQualityTrend(30)
  const { data: deliveryData } = useKpiDelivery()
  const { data: shipmentData } = useKpiShipment()

  const targets = summary?.targets ?? {}

  return (
    <div className="space-y-6">
      <PageHeader
        title="KPI 관리"
        description="생산성, 품질, 납기, 출하 KPI 실집계 대시보드"
      />

      {/* 4종 KPI 카드 */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard
          title="생산 달성률"
          value={summary?.production_rate ?? '-'}
          unit="%"
          status={
            summary && targets.production_rate
              ? summary.production_rate >= targets.production_rate ? 'normal'
              : summary.production_rate >= targets.production_rate * 0.8 ? 'warning'
              : 'critical'
              : 'normal'
          }
          description={targets.production_rate ? `목표 ${targets.production_rate}%` : undefined}
        />
        <KpiCard
          title="불량률"
          value={summary?.defect_rate ?? '-'}
          unit="%"
          changeInverse
          status={
            summary && targets.defect_rate
              ? summary.defect_rate <= targets.defect_rate ? 'normal'
              : summary.defect_rate <= targets.defect_rate * 1.5 ? 'warning'
              : 'critical'
              : 'normal'
          }
          description={targets.defect_rate ? `목표 ≤${targets.defect_rate}%` : undefined}
        />
        <KpiCard
          title="납기 준수율"
          value={deliveryData?.delivery_rate ?? summary?.delivery_rate ?? '-'}
          unit="%"
          status={
            deliveryData && targets.delivery_rate
              ? deliveryData.delivery_rate >= targets.delivery_rate ? 'normal'
              : deliveryData.delivery_rate >= targets.delivery_rate * 0.9 ? 'warning'
              : 'critical'
              : 'normal'
          }
          description={
            deliveryData
              ? `${deliveryData.on_time_orders}/${deliveryData.total_orders}건`
              : undefined
          }
        />
        <KpiCard
          title="당월 출하"
          value={shipmentData?.shipment_count ?? summary?.shipment_count ?? '-'}
          unit="건"
          description={
            shipmentData
              ? `대기 ${shipmentData.pending_count}건 · 인수완료 ${shipmentData.delivered_count}건`
              : undefined
          }
        />
      </div>

      {/* 트렌드 차트 2개 */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border bg-card p-4">
          <h3 className="text-sm font-semibold mb-4">생산 실적 추이 (30일)</h3>
          {prodData && prodData.trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={prodData.trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line
                  dataKey="value"
                  name="생산량"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
              데이터 없음
            </div>
          )}
        </div>

        <div className="rounded-xl border bg-card p-4">
          <h3 className="text-sm font-semibold mb-4">불량률 추이 (30일)</h3>
          {qualData && qualData.trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={qualData.trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} unit="%" />
                <Tooltip formatter={(v: number) => [`${v}%`, '불량률']} />
                <Line
                  dataKey="value"
                  name="불량률"
                  stroke="hsl(var(--destructive))"
                  strokeWidth={2}
                  dot={false}
                />
                {targets.defect_rate && (
                  <Line
                    dataKey={() => targets.defect_rate}
                    name="목표"
                    stroke="hsl(var(--muted-foreground))"
                    strokeDasharray="4 4"
                    strokeWidth={1}
                    dot={false}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
              데이터 없음
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
