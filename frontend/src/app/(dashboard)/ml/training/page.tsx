'use client'

import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PageHeader } from '@/components/ui/page-header'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  useDatasets,
  useTrainingJobs,
  useStartTraining,
  useBuildDataset,
  type AnnotationDatasetRead,
} from '@/lib/hooks/use-ml'
import { TrainingJobCard } from '@/components/ml/training-job-card'
import { useUiStore } from '@/lib/stores/ui-store'
import { formatDistanceToNow } from 'date-fns'
import { ko } from 'date-fns/locale'

const DATASET_STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  building: 'secondary',
  ready: 'default',
  failed: 'destructive',
}

const DATASET_STATUS_LABEL: Record<string, string> = {
  building: '빌드 중',
  ready: '준비됨',
  failed: '실패',
}

export default function TrainingPage() {
  const { setPageTitle } = useUiStore()
  useEffect(() => { setPageTitle('Vision AI 학습 관리') }, [setPageTitle])

  const [trainDialogOpen, setTrainDialogOpen] = useState(false)

  const { data: datasetsData, isLoading: datasetsLoading } = useDatasets()
  const datasets = datasetsData?.data ?? []

  const { data: jobsData, isLoading: jobsLoading } = useTrainingJobs()
  const jobs = jobsData?.data ?? []

  const buildDataset = useBuildDataset()
  const activeJob = jobs.find((j) => j.is_active)

  return (
    <div className="space-y-8">
      <PageHeader
        title="Vision AI 학습 관리"
        description="YOLOv8 모델 학습 데이터셋 빌드 · 학습 실행 · 활성 모델 관리"
        action={
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={buildDataset.isPending}
              onClick={() => buildDataset.mutate()}
            >
              {buildDataset.isPending ? '빌드 중…' : '데이터셋 빌드'}
            </Button>
            <Button size="sm" onClick={() => setTrainDialogOpen(true)}>
              학습 시작
            </Button>
          </div>
        }
      />

      {/* 활성 모델 */}
      {activeJob && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            활성 모델
          </h2>
          <div className="max-w-sm">
            <TrainingJobCard job={activeJob} showActivate={false} />
          </div>
        </section>
      )}

      {/* 데이터셋 목록 */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          데이터셋
        </h2>
        {datasetsLoading ? (
          <div className="py-6 text-center text-sm text-muted-foreground">로딩 중…</div>
        ) : datasets.length === 0 ? (
          <div className="py-6 text-center text-sm text-muted-foreground">
            데이터셋이 없습니다. 어노테이션 완료 후 빌드를 실행하세요.
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {datasets.map((ds) => (
              <DatasetCard key={ds.id} dataset={ds} onStartTrain={() => setTrainDialogOpen(true)} />
            ))}
          </div>
        )}
      </section>

      {/* 학습 이력 */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          학습 이력
        </h2>
        {jobsLoading ? (
          <div className="py-6 text-center text-sm text-muted-foreground">로딩 중…</div>
        ) : jobs.length === 0 ? (
          <div className="py-6 text-center text-sm text-muted-foreground">
            학습 이력이 없습니다.
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {jobs.map((job) => (
              <TrainingJobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </section>

      <StartTrainingDialog
        open={trainDialogOpen}
        onOpenChange={setTrainDialogOpen}
        datasets={datasets.filter((d) => d.status === 'ready')}
      />
    </div>
  )
}

function DatasetCard({
  dataset,
  onStartTrain,
}: {
  dataset: AnnotationDatasetRead
  onStartTrain: () => void
}) {
  const labelEntries = Object.entries(dataset.label_counts ?? {})

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{dataset.version}</CardTitle>
          <Badge variant={DATASET_STATUS_VARIANT[dataset.status]}>
            {DATASET_STATUS_LABEL[dataset.status] ?? dataset.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="text-xs text-muted-foreground">
          이미지 {dataset.image_count}장
        </div>
        {labelEntries.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {labelEntries.map(([label, count]) => (
              <span
                key={label}
                className="rounded-full bg-secondary px-2 py-0.5 text-xs text-secondary-foreground"
              >
                {label}: {count}
              </span>
            ))}
          </div>
        )}
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            {dataset.built_at
              ? formatDistanceToNow(new Date(dataset.built_at), { addSuffix: true, locale: ko })
              : formatDistanceToNow(new Date(dataset.created_at), { addSuffix: true, locale: ko })}
          </p>
          {dataset.status === 'ready' && (
            <Button size="sm" variant="outline" className="h-7 text-xs" onClick={onStartTrain}>
              학습 시작
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

interface StartTrainingDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  datasets: AnnotationDatasetRead[]
}

function StartTrainingDialog({ open, onOpenChange, datasets }: StartTrainingDialogProps) {
  const [datasetId, setDatasetId] = useState('')
  const [modelVersion, setModelVersion] = useState('yolov8n')
  const [epochs, setEpochs] = useState('100')
  const [batchSize, setBatchSize] = useState('16')
  const [imgSize, setImgSize] = useState('640')

  const startTraining = useStartTraining()

  const handleStart = () => {
    if (!datasetId) return
    startTraining.mutate(
      {
        dataset_id: datasetId,
        model_version: modelVersion,
        epochs: parseInt(epochs),
        batch_size: parseInt(batchSize),
        img_size: parseInt(imgSize),
      },
      { onSuccess: () => onOpenChange(false) }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>YOLOv8 학습 시작</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>데이터셋 *</Label>
            <Select value={datasetId} onValueChange={setDatasetId}>
              <SelectTrigger>
                <SelectValue placeholder="데이터셋을 선택하세요" />
              </SelectTrigger>
              <SelectContent>
                {datasets.map((ds) => (
                  <SelectItem key={ds.id} value={ds.id}>
                    {ds.version} ({ds.image_count}장)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>모델 버전</Label>
            <Select value={modelVersion} onValueChange={setModelVersion}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {['yolov8n', 'yolov8s', 'yolov8m', 'yolov8l'].map((v) => (
                  <SelectItem key={v} value={v}>{v}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Epochs</Label>
              <Input
                type="number"
                value={epochs}
                onChange={(e) => setEpochs(e.target.value)}
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Batch Size</Label>
              <Input
                type="number"
                value={batchSize}
                onChange={(e) => setBatchSize(e.target.value)}
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Img Size</Label>
              <Input
                type="number"
                value={imgSize}
                onChange={(e) => setImgSize(e.target.value)}
                className="h-8 text-sm"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              취소
            </Button>
            <Button
              disabled={!datasetId || startTraining.isPending}
              onClick={handleStart}
            >
              {startTraining.isPending ? '시작 중…' : '학습 시작'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
