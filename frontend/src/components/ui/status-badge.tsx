import * as React from 'react'

// ============================================================
// 상태 배지 컴포넌트
// ============================================================

const STATUS_STYLES: Record<string, string> = {
  // Equipment
  running:
    'bg-green-100 text-green-700 dark:bg-green-950/50 dark:text-green-400',
  idle: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
  maintenance:
    'bg-yellow-100 text-yellow-700 dark:bg-yellow-950/50 dark:text-yellow-400',
  breakdown:
    'bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-400',
  decommissioned: 'bg-gray-200 text-gray-500',
  // Work Order
  pending:
    'bg-blue-100 text-blue-700 dark:bg-blue-950/50 dark:text-blue-400',
  in_progress:
    'bg-yellow-100 text-yellow-700 dark:bg-yellow-950/50 dark:text-yellow-400',
  completed:
    'bg-green-100 text-green-700 dark:bg-green-950/50 dark:text-green-400',
  on_hold:
    'bg-orange-100 text-orange-700 dark:bg-orange-950/50 dark:text-orange-400',
  cancelled: 'bg-gray-100 text-gray-700',
  // Supplier grade
  A: 'bg-emerald-100 text-emerald-700',
  B: 'bg-blue-100 text-blue-700',
  C: 'bg-yellow-100 text-yellow-700',
  D: 'bg-red-100 text-red-700',
}

const STATUS_LABELS: Record<string, string> = {
  running: '가동 중',
  idle: '대기',
  maintenance: '점검 중',
  breakdown: '고장',
  decommissioned: '폐기',
  pending: '대기',
  in_progress: '진행 중',
  completed: '완료',
  on_hold: '보류',
  cancelled: '취소',
  A: 'A등급',
  B: 'B등급',
  C: 'C등급',
  D: 'D등급',
}

interface StatusBadgeProps {
  status: string
  label?: string
  className?: string
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const style = STATUS_STYLES[status] ?? 'bg-gray-100 text-gray-700'
  const text = label ?? STATUS_LABELS[status] ?? status
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${style} ${className ?? ''}`}
    >
      {text}
    </span>
  )
}
