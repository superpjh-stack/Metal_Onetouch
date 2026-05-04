import { cn } from '@/lib/utils'

type RiskLevel = 'GREEN' | 'YELLOW' | 'RED'

interface RiskBadgeProps {
  level: RiskLevel
  showLabel?: boolean
  className?: string
}

const RISK_CONFIG: Record<RiskLevel, { label: string; className: string; dot: string }> = {
  GREEN: {
    label: '정상',
    className: 'bg-green-100 text-green-800 border-green-200',
    dot: 'bg-green-500',
  },
  YELLOW: {
    label: '주의',
    className: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    dot: 'bg-yellow-500',
  },
  RED: {
    label: '중지',
    className: 'bg-red-100 text-red-800 border-red-200',
    dot: 'bg-red-500',
  },
}

export function RiskBadge({ level, showLabel = true, className }: RiskBadgeProps) {
  const config = RISK_CONFIG[level]

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold',
        config.className,
        className
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', config.dot)} />
      {level}
      {showLabel && <span className="text-xs font-normal opacity-70">({config.label})</span>}
    </span>
  )
}
