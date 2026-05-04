'use client'

import { useDrawingStatus } from '@/lib/hooks/use-cad'
import { StatusBadge } from '@/components/ui/status-badge'

const STATUS_LABEL: Record<string, string> = {
  pending:   '분석 대기',
  analyzing: 'AI 분석 중',
  completed: '분석 완료',
  failed:    '분석 실패',
}

interface DrawingAnalysisCardProps {
  drawingId: string
  onCompleted?: () => void
}

export function DrawingAnalysisCard({ drawingId, onCompleted }: DrawingAnalysisCardProps) {
  const { data: status, isLoading } = useDrawingStatus(drawingId)

  if (isLoading) {
    return (
      <div className="rounded-lg border bg-white p-4 dark:bg-gray-900">
        <div className="h-4 w-32 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
      </div>
    )
  }

  if (!status) return null

  const isCompleted = status.analysis_status === 'completed'
  const isFailed = status.analysis_status === 'failed'

  if (isCompleted && onCompleted) {
    onCompleted()
  }

  return (
    <div className="rounded-lg border bg-white p-4 dark:bg-gray-900">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-500">도면 번호</p>
          <p className="font-mono text-sm font-medium">{status.drawing_number}</p>
        </div>
        <StatusBadge
          status={status.analysis_status}
          label={STATUS_LABEL[status.analysis_status]}
        />
      </div>

      {!isCompleted && !isFailed && (
        <div className="mt-3">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
            <div className="h-full animate-pulse rounded-full bg-blue-500" style={{ width: '60%' }} />
          </div>
          <p className="mt-1 text-xs text-gray-500">GPT-4o Vision으로 도면을 분석하는 중입니다…</p>
        </div>
      )}

      {isFailed && status.error_message && (
        <p className="mt-2 text-xs text-red-500">{status.error_message}</p>
      )}

      {isCompleted && status.analyzed_at && (
        <p className="mt-2 text-xs text-gray-500">
          분석 완료: {new Date(status.analyzed_at).toLocaleString('ko-KR')}
        </p>
      )}
    </div>
  )
}
