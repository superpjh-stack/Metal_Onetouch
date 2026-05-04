'use client'

import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/ui/page-header'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { DataTable } from '@/components/ui/data-table'
import { useAnnotationTasks, type AnnotationTaskRead } from '@/lib/hooks/use-annotation'
import { AnnotationEditor } from '@/components/ml/annotation-editor'
import { useUiStore } from '@/lib/stores/ui-store'
import { formatDistanceToNow } from 'date-fns'
import { ko } from 'date-fns/locale'

const STATUS_LABEL: Record<string, string> = {
  pending: '대기 중',
  in_progress: '진행 중',
  completed: '완료',
  skipped: '건너뜀',
}

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  pending: 'secondary',
  in_progress: 'default',
  completed: 'outline',
  skipped: 'outline',
}

export default function AnnotationPage() {
  const { setPageTitle } = useUiStore()
  useEffect(() => { setPageTitle('어노테이션 관리') }, [setPageTitle])

  const [statusFilter, setStatusFilter] = useState<string>('pending')
  const [selectedTask, setSelectedTask] = useState<AnnotationTaskRead | null>(null)
  const [page, setPage] = useState(1)
  const LIMIT = 20

  const { data, isLoading } = useAnnotationTasks({
    status: statusFilter === 'all' ? undefined : statusFilter,
    page,
    limit: LIMIT,
  })
  const tasks = data?.data ?? []
  const total = data?.total ?? 0

  return (
    <div className="space-y-6">
      <PageHeader
        title="어노테이션 관리"
        description="AI 분석 결과를 검토하고 보정하여 학습 데이터를 개선합니다"
      />

      <div className="flex items-center gap-3">
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1) }}>
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">전체</SelectItem>
            <SelectItem value="pending">대기 중</SelectItem>
            <SelectItem value="in_progress">진행 중</SelectItem>
            <SelectItem value="completed">완료</SelectItem>
            <SelectItem value="skipped">건너뜀</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-sm text-muted-foreground">총 {total}건</span>
      </div>

      <DataTable<AnnotationTaskRead>
        isLoading={isLoading}
        data={tasks}
        columns={[
          {
            key: 'drawing_id',
            header: '도면 ID',
            cell: (row) => (
              <span className="font-mono text-xs">{row.drawing_id.slice(0, 8)}…</span>
            ),
          },
          {
            key: 'status',
            header: '상태',
            cell: (row) => (
              <Badge variant={STATUS_VARIANT[row.status]}>
                {STATUS_LABEL[row.status] ?? row.status}
              </Badge>
            ),
          },
          {
            key: 'created_at',
            header: '생성일',
            cell: (row) =>
              formatDistanceToNow(new Date(row.created_at), { addSuffix: true, locale: ko }),
          },
          {
            key: 'completed_at',
            header: '완료일',
            cell: (row) =>
              row.completed_at
                ? new Date(row.completed_at).toLocaleDateString('ko-KR')
                : '-',
          },
          {
            key: 'id',
            header: '',
            cell: (row) =>
              row.status === 'pending' || row.status === 'in_progress' ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setSelectedTask(row)}
                >
                  보정
                </Button>
              ) : null,
          },
        ]}
      />

      {total > LIMIT && (
        <div className="flex justify-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
          >
            이전
          </Button>
          <span className="flex items-center px-3 text-sm">
            {page} / {Math.ceil(total / LIMIT)}
          </span>
          <Button
            size="sm"
            variant="outline"
            disabled={page * LIMIT >= total}
            onClick={() => setPage((p) => p + 1)}
          >
            다음
          </Button>
        </div>
      )}

      <Sheet open={!!selectedTask} onOpenChange={(open) => { if (!open) setSelectedTask(null) }}>
        <SheetContent side="right" className="w-full sm:max-w-xl overflow-y-auto">
          <SheetHeader className="mb-4">
            <SheetTitle>어노테이션 보정</SheetTitle>
            {selectedTask && (
              <p className="text-xs text-muted-foreground font-mono">
                도면 ID: {selectedTask.drawing_id}
              </p>
            )}
          </SheetHeader>
          {selectedTask && (
            <AnnotationEditor
              drawingId={selectedTask.drawing_id}
              originalParsed={
                (selectedTask.corrected_parsed ?? selectedTask.original_parsed) as Parameters<
                  typeof AnnotationEditor
                >[0]['originalParsed']
              }
              onSubmit={() => setSelectedTask(null)}
            />
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
