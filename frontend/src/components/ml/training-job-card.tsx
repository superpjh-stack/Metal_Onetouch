'use client'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { useActivateModel, useTrainingJobStatus, type TrainingJobRead } from '@/lib/hooks/use-ml'
import { formatDistanceToNow } from 'date-fns'
import { ko } from 'date-fns/locale'

interface TrainingJobCardProps {
  job: TrainingJobRead
  showActivate?: boolean
}

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  pending: 'secondary',
  running: 'default',
  completed: 'default',
  failed: 'destructive',
}

const STATUS_LABEL: Record<string, string> = {
  pending: '대기 중',
  running: '학습 중',
  completed: '완료',
  failed: '실패',
}

export function TrainingJobCard({ job: initialJob, showActivate = true }: TrainingJobCardProps) {
  const { data: polledJob } = useTrainingJobStatus(
    initialJob.status === 'running' || initialJob.status === 'pending'
      ? initialJob.id
      : undefined
  )
  const job = polledJob ?? initialJob
  const activate = useActivateModel()

  const elapsedMs = job.started_at
    ? Date.now() - new Date(job.started_at).getTime()
    : 0
  const elapsedMin = Math.floor(elapsedMs / 60000)

  return (
    <Card className={job.is_active ? 'border-primary' : ''}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">
            {job.model_version} — {new Date(job.created_at).toLocaleDateString('ko-KR')}
          </CardTitle>
          <div className="flex items-center gap-2">
            {job.is_active && (
              <Badge variant="outline" className="border-primary text-primary text-xs">
                활성
              </Badge>
            )}
            <Badge variant={STATUS_VARIANT[job.status]} className="text-xs">
              {STATUS_LABEL[job.status] ?? job.status}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-2">
        <div className="text-xs text-muted-foreground">
          epochs: {job.epochs} · batch: {job.batch_size} · img: {job.img_size}
        </div>

        {job.status === 'running' && (
          <div className="space-y-1">
            <Progress value={undefined} className="h-1.5 animate-pulse" />
            <p className="text-xs text-muted-foreground">경과: {elapsedMin}분</p>
          </div>
        )}

        {job.status === 'completed' && job.val_map50 != null && (
          <div className="flex items-center gap-4">
            <div>
              <p className="text-xs text-muted-foreground">val mAP@0.5</p>
              <p className="text-lg font-bold text-primary">
                {(job.val_map50 * 100).toFixed(1)}%
              </p>
            </div>
            {job.train_map50 != null && (
              <div>
                <p className="text-xs text-muted-foreground">train mAP@0.5</p>
                <p className="text-sm font-medium">{(job.train_map50 * 100).toFixed(1)}%</p>
              </div>
            )}
          </div>
        )}

        {job.status === 'failed' && job.error_message && (
          <p className="rounded bg-destructive/10 px-2 py-1 text-xs text-destructive">
            {job.error_message.slice(0, 100)}
          </p>
        )}

        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            {formatDistanceToNow(new Date(job.created_at), { addSuffix: true, locale: ko })}
          </p>

          {showActivate && job.status === 'completed' && !job.is_active && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              disabled={activate.isPending}
              onClick={() => activate.mutate(job.id)}
            >
              모델 활성화
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
