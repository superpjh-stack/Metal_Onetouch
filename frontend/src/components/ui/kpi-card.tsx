import * as React from 'react'
import { type LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/lib/utils/format'

// ============================================================
// KPI 카드 컴포넌트
// ============================================================

export interface KpiCardProps {
  title: string
  value: string | number
  unit?: string
  /** 전일 대비 변화율 (%) — 양수: 상승, 음수: 하락 */
  change?: number
  /** 변화율 방향과 비즈니스 의미가 다를 때 사용 (예: 불량률은 낮을수록 good) */
  changeInverse?: boolean
  status?: 'normal' | 'warning' | 'critical'
  icon?: LucideIcon
  description?: string
  isLoading?: boolean
  className?: string
}

const statusStyles = {
  normal: 'border-l-green-500',
  warning: 'border-l-yellow-500',
  critical: 'border-l-red-500',
}

const statusBgStyles = {
  normal: 'bg-green-50 dark:bg-green-950/20',
  warning: 'bg-yellow-50 dark:bg-yellow-950/20',
  critical: 'bg-red-50 dark:bg-red-950/20',
}

export function KpiCard({
  title,
  value,
  unit,
  change,
  changeInverse = false,
  status = 'normal',
  icon: Icon,
  description,
  isLoading = false,
  className,
}: KpiCardProps) {
  // 변화 방향 결정
  const isPositiveChange = change !== undefined ? change >= 0 : null
  // 비즈니스적으로 긍정 여부 (changeInverse=true이면 하락이 긍정)
  const isGoodChange =
    change !== undefined
      ? changeInverse
        ? change <= 0
        : change >= 0
      : null

  return (
    <div
      className={cn(
        'rounded-xl border bg-card text-card-foreground shadow-sm',
        'border-l-4 p-5 transition-all duration-200 hover:shadow-md',
        statusStyles[status],
        className
      )}
    >
      {isLoading ? (
        <KpiCardSkeleton />
      ) : (
        <>
          {/* 헤더: 제목 + 아이콘 */}
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-sm font-medium text-muted-foreground truncate">
                {title}
              </p>
            </div>
            {Icon && (
              <div
                className={cn(
                  'flex h-9 w-9 items-center justify-center rounded-lg',
                  statusBgStyles[status]
                )}
              >
                <Icon className="h-5 w-5 text-muted-foreground" />
              </div>
            )}
          </div>

          {/* 값 */}
          <div className="mt-3 flex items-baseline gap-1">
            <span className="text-3xl font-bold tracking-tight text-foreground">
              {typeof value === 'number' ? value.toLocaleString('ko-KR') : value}
            </span>
            {unit && (
              <span className="text-sm font-medium text-muted-foreground">
                {unit}
              </span>
            )}
          </div>

          {/* 변화율 + 설명 */}
          <div className="mt-2 flex items-center gap-2">
            {change !== undefined && (
              <div
                className={cn(
                  'flex items-center gap-0.5 text-xs font-medium',
                  isGoodChange ? 'text-green-600' : 'text-red-600'
                )}
              >
                {isPositiveChange ? (
                  <TrendingUp className="h-3.5 w-3.5" />
                ) : change === 0 ? (
                  <Minus className="h-3.5 w-3.5" />
                ) : (
                  <TrendingDown className="h-3.5 w-3.5" />
                )}
                <span>
                  {change > 0 ? '+' : ''}
                  {change.toFixed(1)}%
                </span>
              </div>
            )}
            {description && (
              <p className="text-xs text-muted-foreground truncate">
                {description}
              </p>
            )}
            {!description && change !== undefined && (
              <p className="text-xs text-muted-foreground">전일 대비</p>
            )}
          </div>
        </>
      )}
    </div>
  )
}

// ============================================================
// 스켈레톤 로딩 상태
// ============================================================

function KpiCardSkeleton() {
  return (
    <div className="animate-skeleton-pulse space-y-3">
      <div className="flex items-start justify-between">
        <div className="h-4 w-24 rounded bg-muted" />
        <div className="h-9 w-9 rounded-lg bg-muted" />
      </div>
      <div className="h-9 w-32 rounded bg-muted" />
      <div className="h-3 w-20 rounded bg-muted" />
    </div>
  )
}
