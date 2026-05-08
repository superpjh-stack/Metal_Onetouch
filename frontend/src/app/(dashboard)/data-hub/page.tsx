'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import {
  Database,
  Wifi,
  WifiOff,
  Activity,
  Thermometer,
  Zap,
  Gauge,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  ArrowRight,
  Server,
} from 'lucide-react'
import { useUiStore } from '@/lib/stores/ui-store'
import { PageHeader } from '@/components/ui/page-header'

// ============================================================
// 타입
// ============================================================

interface SensorReading {
  time: string
  temperature: number
  pressure: number
  vibration: number
  power: number
}

interface PipelineNode {
  name: string
  status: 'running' | 'degraded' | 'stopped'
  throughput: string
  latency: string
  icon: React.ComponentType<{ className?: string }>
}

interface SensorAlert {
  id: string
  sensor: string
  metric: string
  value: string
  threshold: string
  level: 'warning' | 'critical'
  time: string
}

// ============================================================
// 시뮬레이션 헬퍼
// ============================================================

function randAround(base: number, range: number) {
  return parseFloat((base + (Math.random() - 0.5) * range * 2).toFixed(2))
}

function timeLabel() {
  const d = new Date()
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`
}

function generateReading(): SensorReading {
  return {
    time: timeLabel(),
    temperature: randAround(72, 8),
    pressure: randAround(4.2, 0.6),
    vibration: randAround(1.8, 0.5),
    power: randAround(85, 10),
  }
}

function generateHistory(): SensorReading[] {
  const now = new Date()
  return Array.from({ length: 20 }, (_, i) => {
    const d = new Date(now.getTime() - (19 - i) * 3000)
    return {
      time: `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`,
      temperature: randAround(72, 8),
      pressure: randAround(4.2, 0.6),
      vibration: randAround(1.8, 0.5),
      power: randAround(85, 10),
    }
  })
}

const PIPELINE_NODES: PipelineNode[] = [
  { name: 'MQTT Broker', status: 'running', throughput: '1,240 msg/s', latency: '2 ms', icon: Wifi },
  { name: 'Kafka', status: 'running', throughput: '1,210 msg/s', latency: '8 ms', icon: Activity },
  { name: 'Flink', status: 'degraded', throughput: '980 msg/s', latency: '45 ms', icon: Zap },
  { name: 'TimescaleDB', status: 'running', throughput: '950 rows/s', latency: '12 ms', icon: Database },
]

const INITIAL_ALERTS: SensorAlert[] = [
  { id: '1', sensor: 'CNC-003', metric: '온도', value: '84.3°C', threshold: '80°C', level: 'warning', time: '14:32:05' },
  { id: '2', sensor: 'PRESS-001', metric: '진동', value: '3.1 g', threshold: '3.0 g', level: 'critical', time: '14:28:41' },
  { id: '3', sensor: 'WELD-002', metric: '전력', value: '98.2 kW', threshold: '95 kW', level: 'warning', time: '14:15:20' },
]

const DAILY_VOLUME = [
  { hour: '00', rows: 410000 },
  { hour: '04', rows: 390000 },
  { hour: '08', rows: 820000 },
  { hour: '10', rows: 1050000 },
  { hour: '12', rows: 980000 },
  { hour: '14', rows: 1120000 },
  { hour: '16', rows: 870000 },
  { hour: '18', rows: 640000 },
  { hour: '20', rows: 510000 },
  { hour: '22', rows: 430000 },
]

// ============================================================
// 서브 컴포넌트
// ============================================================

function StatusDot({ status }: { status: PipelineNode['status'] }) {
  const cls =
    status === 'running'
      ? 'bg-green-500'
      : status === 'degraded'
      ? 'bg-yellow-500'
      : 'bg-red-500'
  return (
    <span className="relative flex h-2 w-2">
      {status === 'running' && (
        <span className={`absolute inline-flex h-full w-full animate-ping rounded-full ${cls} opacity-60`} />
      )}
      <span className={`relative inline-flex h-2 w-2 rounded-full ${cls}`} />
    </span>
  )
}

function MetricCard({
  label,
  value,
  unit,
  icon: Icon,
  status,
}: {
  label: string
  value: number
  unit: string
  icon: React.ComponentType<{ className?: string }>
  status: 'normal' | 'warning' | 'critical'
}) {
  const color =
    status === 'critical'
      ? 'text-red-500'
      : status === 'warning'
      ? 'text-yellow-500'
      : 'text-green-500'

  return (
    <div className="rounded-xl border bg-card p-4 flex items-center gap-4">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
        <Icon className="h-5 w-5 text-muted-foreground" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className={`text-xl font-bold ${color}`}>
          {value}
          <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>
        </p>
      </div>
      <div className={`w-2 h-8 rounded-full ${status === 'critical' ? 'bg-red-500' : status === 'warning' ? 'bg-yellow-500' : 'bg-green-500'}`} />
    </div>
  )
}

// ============================================================
// 메인 페이지
// ============================================================

export default function DataHubPage() {
  const { setPageTitle } = useUiStore()
  const [history, setHistory] = useState<SensorReading[]>(generateHistory)
  const [latest, setLatest] = useState<SensorReading>(() => generateReading())
  const [alerts] = useState<SensorAlert[]>(INITIAL_ALERTS)
  const [isLive, setIsLive] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(new Date())

  useEffect(() => { setPageTitle('데이터허브') }, [setPageTitle])

  const tick = useCallback(() => {
    const reading = generateReading()
    setLatest(reading)
    setHistory((prev) => [...prev.slice(-29), reading])
    setLastUpdated(new Date())
  }, [])

  useEffect(() => {
    if (!isLive) return
    const id = setInterval(tick, 2000)
    return () => clearInterval(id)
  }, [isLive, tick])

  type MetricStatus = 'normal' | 'warning' | 'critical'
  const latestMetrics: { label: string; value: number; unit: string; icon: React.ComponentType<{ className?: string }>; status: MetricStatus }[] = [
    { label: '평균 온도', value: latest.temperature, unit: '°C', icon: Thermometer, status: latest.temperature > 78 ? 'warning' : 'normal' },
    { label: '평균 압력', value: latest.pressure, unit: 'bar', icon: Gauge, status: latest.pressure > 4.6 ? 'warning' : 'normal' },
    { label: '평균 진동', value: latest.vibration, unit: 'g', icon: Activity, status: latest.vibration > 2.8 ? 'critical' : latest.vibration > 2.2 ? 'warning' : 'normal' },
    { label: '평균 전력', value: latest.power, unit: 'kW', icon: Zap, status: latest.power > 93 ? 'warning' : 'normal' },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="데이터허브"
        description="IoT 센서 실시간 데이터 · 시계열 분석 · 파이프라인 모니터링"
        action={
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsLive((v) => !v)}
              className={[
                'flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors',
                isLive
                  ? 'bg-green-100 text-green-700 dark:bg-green-950/40 dark:text-green-400'
                  : 'bg-muted text-muted-foreground',
              ].join(' ')}
            >
              {isLive ? (
                <>
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
                  </span>
                  실시간 ON
                </>
              ) : (
                <>
                  <WifiOff className="h-3.5 w-3.5" />
                  일시정지
                </>
              )}
            </button>
            <button
              onClick={tick}
              className="flex items-center gap-1.5 rounded-lg border bg-card px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              갱신
            </button>
            <span className="text-xs text-muted-foreground">
              {lastUpdated.toLocaleTimeString('ko-KR')} 기준
            </span>
          </div>
        }
      />

      {/* KPI 메트릭 카드 */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {latestMetrics.map((m) => (
          <MetricCard key={m.label} {...m} />
        ))}
      </div>

      {/* 실시간 차트 + 파이프라인 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">

        {/* 온도 실시간 라인 차트 */}
        <div className="lg:col-span-2 rounded-xl border bg-card p-5">
          <div className="mb-4">
            <h3 className="text-base font-semibold text-foreground">설비 온도 실시간 모니터링</h3>
            <p className="text-xs text-muted-foreground">최근 60초 · 기준치 80°C</p>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={history} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="time"
                tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
                interval={4}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={[50, 100]}
                tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
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
                formatter={(v: number) => [`${v}°C`, '온도']}
              />
              <ReferenceLine y={80} stroke="#ef4444" strokeDasharray="4 4" strokeWidth={1.5} label={{ value: '기준치', position: 'insideTopRight', fontSize: 10, fill: '#ef4444' }} />
              <Line
                type="monotone"
                dataKey="temperature"
                stroke="#f97316"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* 데이터 파이프라인 상태 */}
        <div className="rounded-xl border bg-card p-5">
          <div className="mb-4">
            <h3 className="text-base font-semibold text-foreground">데이터 파이프라인</h3>
            <p className="text-xs text-muted-foreground">MQTT → Kafka → Flink → DB</p>
          </div>
          <div className="space-y-2">
            {PIPELINE_NODES.map((node, i) => {
              const Icon = node.icon
              return (
                <div key={node.name}>
                  <div className="rounded-lg border bg-muted/30 p-3">
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <Icon className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm font-medium text-foreground">{node.name}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <StatusDot status={node.status} />
                        <span className={`text-xs font-medium ${node.status === 'running' ? 'text-green-600 dark:text-green-400' : node.status === 'degraded' ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}`}>
                          {node.status === 'running' ? '정상' : node.status === 'degraded' ? '저하' : '중단'}
                        </span>
                      </div>
                    </div>
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>{node.throughput}</span>
                      <span>지연 {node.latency}</span>
                    </div>
                  </div>
                  {i < PIPELINE_NODES.length - 1 && (
                    <div className="flex justify-center py-0.5">
                      <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/40 rotate-90" />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* 압력/진동 차트 + 알림 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">

        {/* 압력 + 진동 차트 */}
        <div className="lg:col-span-2 rounded-xl border bg-card p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-foreground">압력 / 진동 추이</h3>
              <p className="text-xs text-muted-foreground">최근 60초 실시간</p>
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-blue-500 inline-block" /> 압력(bar)</span>
              <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-purple-500 inline-block" /> 진동(g)</span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={history} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="time"
                tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
                interval={4}
                axisLine={false}
                tickLine={false}
              />
              <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
                formatter={(v: number, name: string) => [v, name === 'pressure' ? '압력(bar)' : '진동(g)']}
              />
              <Line type="monotone" dataKey="pressure" stroke="#3b82f6" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="vibration" stroke="#a855f7" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* 센서 알림 */}
        <div className="rounded-xl border bg-card p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-foreground">센서 알림</h3>
              <p className="text-xs text-muted-foreground">임계값 초과 이벤트</p>
            </div>
            <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-950/40 dark:text-red-400">
              {alerts.length}건
            </span>
          </div>
          <div className="space-y-2">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={`rounded-lg border p-3 ${alert.level === 'critical' ? 'border-red-200 bg-red-50/50 dark:border-red-900/40 dark:bg-red-950/20' : 'border-yellow-200 bg-yellow-50/50 dark:border-yellow-900/40 dark:bg-yellow-950/20'}`}
              >
                <div className="flex items-start gap-2">
                  <AlertTriangle className={`h-4 w-4 mt-0.5 shrink-0 ${alert.level === 'critical' ? 'text-red-500' : 'text-yellow-500'}`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-foreground">{alert.sensor}</span>
                      <span className="text-[10px] text-muted-foreground">{alert.time}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {alert.metric}: <span className="font-medium text-foreground">{alert.value}</span>
                      {' '}(기준 {alert.threshold})
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400">
            <CheckCircle2 className="h-3.5 w-3.5" />
            나머지 32개 센서 정상 운행 중
          </div>
        </div>
      </div>

      {/* 일별 데이터 처리량 */}
      <div className="rounded-xl border bg-card p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-foreground">오늘 시간대별 데이터 처리량</h3>
            <p className="text-xs text-muted-foreground">TimescaleDB 삽입 rows/시간</p>
          </div>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <Server className="h-3.5 w-3.5" />
              <span>누적 <strong className="text-foreground">8.7M</strong> rows</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Database className="h-3.5 w-3.5" />
              <span>저장 <strong className="text-foreground">12.4 GB</strong></span>
            </div>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={DAILY_VOLUME} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
            <XAxis
              dataKey="hour"
              tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              tickFormatter={(v) => `${v}시`}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              formatter={(v: number) => [`${v.toLocaleString('ko-KR')} rows`, '처리량']}
              labelFormatter={(l) => `${l}시`}
            />
            <Bar dataKey="rows" fill="#3b82f6" radius={[4, 4, 0, 0]} maxBarSize={40} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
