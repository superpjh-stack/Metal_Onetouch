'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Clock, User, Wrench } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DataTable } from '@/components/ui/data-table'
import { StatusBadge } from '@/components/ui/status-badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useUiStore } from '@/lib/stores/ui-store'
import {
  useWorkOrder,
  useUpdateWorkOrderStatus,
  useAddProcessResult,
} from '@/lib/hooks/use-work-orders'
import { formatDateTime } from '@/lib/utils/format'
import type { ProcessResult } from '@/types'

// ============================================================
// 작업지시 상세 페이지
// ============================================================

// 허용 상태 전환 매핑
const ALLOWED_TRANSITIONS: Record<string, { to: string; label: string }[]> = {
  pending: [
    { to: 'in_progress', label: '작업 시작' },
    { to: 'cancelled', label: '취소' },
  ],
  in_progress: [
    { to: 'completed', label: '완료 처리' },
    { to: 'on_hold', label: '보류' },
  ],
  on_hold: [
    { to: 'in_progress', label: '재개' },
    { to: 'cancelled', label: '취소' },
  ],
  completed: [],
  cancelled: [],
}

export default function WorkOrderDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { setPageTitle } = useUiStore()
  const woId = String(params.wo_id)

  const { data: wo, isLoading } = useWorkOrder(woId)
  const { mutate: updateStatus, isPending: statusPending } =
    useUpdateWorkOrderStatus()
  const [resultDialogOpen, setResultDialogOpen] = useState(false)

  useEffect(() => {
    setPageTitle(wo ? `작업지시 ${wo.wo_number}` : '작업지시 상세')
  }, [setPageTitle, wo])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-2 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  if (!wo) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <p className="text-muted-foreground">작업지시를 찾을 수 없습니다.</p>
        <Button variant="outline" onClick={() => router.push('/process')}>
          목록으로 돌아가기
        </Button>
      </div>
    )
  }

  const transitions = ALLOWED_TRANSITIONS[wo.status] ?? []

  return (
    <div className="space-y-6">
      {/* 상단 헤더 */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push('/process')}
          aria-label="목록으로"
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-foreground">
              {wo.wo_number}
            </h2>
            <StatusBadge status={wo.status} />
          </div>
          <p className="mt-0.5 text-sm text-muted-foreground font-mono">
            LOT: {wo.lot_display_id ?? wo.lot_id}
          </p>
        </div>
        {/* 상태 전환 버튼들 */}
        <div className="flex items-center gap-2">
          {transitions.map((t) => (
            <Button
              key={t.to}
              variant={t.to === 'cancelled' ? 'outline' : 'default'}
              disabled={statusPending}
              onClick={() => updateStatus({ id: wo.id, status: t.to })}
            >
              {t.label}
            </Button>
          ))}
        </div>
      </div>

      {/* WO 상세 정보 카드 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <InfoCard
          icon={<Wrench className="h-4 w-4" />}
          label="공정"
          value={wo.process_name ?? '-'}
        />
        <InfoCard
          icon={<User className="h-4 w-4" />}
          label="담당자"
          value={wo.assigned_name ?? '-'}
        />
        <InfoCard
          icon={<Wrench className="h-4 w-4" />}
          label="설비"
          value={wo.equipment_name ?? '-'}
        />
        <InfoCard
          icon={<Clock className="h-4 w-4" />}
          label="계획 시작"
          value={wo.planned_start ? formatDateTime(wo.planned_start) : '-'}
        />
        <InfoCard
          icon={<Clock className="h-4 w-4" />}
          label="계획 종료"
          value={wo.planned_end ? formatDateTime(wo.planned_end) : '-'}
        />
        <InfoCard
          icon={<Clock className="h-4 w-4" />}
          label="실제 시작"
          value={wo.actual_start ? formatDateTime(wo.actual_start) : '-'}
        />
      </div>

      {/* 수량 현황 */}
      <div className="rounded-xl border bg-card p-5">
        <h3 className="mb-4 text-base font-semibold">수량 현황</h3>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-sm text-muted-foreground">투입수량</p>
            <p className="text-2xl font-bold">
              {wo.input_qty?.toLocaleString('ko-KR') ?? '-'}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">산출수량</p>
            <p className="text-2xl font-bold text-green-600">
              {wo.output_qty?.toLocaleString('ko-KR') ?? '-'}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">불량수량</p>
            <p className="text-2xl font-bold text-red-600">
              {wo.defect_qty.toLocaleString('ko-KR')}
            </p>
          </div>
        </div>
      </div>

      {/* 공정 실적 이력 */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-base font-semibold">공정 실적 이력</h3>
          {wo.status === 'in_progress' && (
            <Button
              size="sm"
              onClick={() => setResultDialogOpen(true)}
            >
              공정 실적 등록
            </Button>
          )}
        </div>

        <DataTable<ProcessResult>
          data={wo.process_results ?? []}
          columns={[
            {
              key: 'worker_name',
              header: '작업자',
              cell: (row) => row.worker_name ?? '-',
            },
            {
              key: 'input_qty',
              header: '투입',
              cell: (row) => row.input_qty.toLocaleString('ko-KR'),
            },
            {
              key: 'output_qty',
              header: '산출',
              cell: (row) => row.output_qty.toLocaleString('ko-KR'),
            },
            {
              key: 'defect_qty',
              header: '불량',
              cell: (row) => row.defect_qty.toLocaleString('ko-KR'),
            },
            {
              key: 'start_time',
              header: '시작시간',
              cell: (row) => formatDateTime(row.start_time),
            },
            {
              key: 'end_time',
              header: '종료시간',
              cell: (row) => formatDateTime(row.end_time),
            },
            {
              key: 'condition_notes',
              header: '비고',
              cell: (row) => row.condition_notes ?? '-',
            },
          ]}
          emptyMessage="등록된 공정 실적이 없습니다."
        />
      </div>

      {/* 공정 실적 등록 다이얼로그 */}
      <AddProcessResultDialog
        woId={wo.id}
        open={resultDialogOpen}
        onOpenChange={setResultDialogOpen}
      />
    </div>
  )
}

// ============================================================
// 정보 카드 서브 컴포넌트
// ============================================================

function InfoCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string
}) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center gap-2 text-muted-foreground">
        {icon}
        <span className="text-xs font-medium">{label}</span>
      </div>
      <p className="mt-2 text-sm font-semibold text-foreground">{value}</p>
    </div>
  )
}

// ============================================================
// 공정 실적 등록 다이얼로그
// ============================================================

interface AddProcessResultDialogProps {
  woId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

function AddProcessResultDialog({
  woId,
  open,
  onOpenChange,
}: AddProcessResultDialogProps) {
  const { mutate, isPending } = useAddProcessResult(woId)
  const [form, setForm] = useState({
    input_qty: 0,
    output_qty: 0,
    defect_qty: 0,
    start_time: '',
    end_time: '',
    condition_notes: '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutate(
      {
        ...form,
        work_order_id: woId,
        lot_id: '',
      },
      { onSuccess: () => onOpenChange(false) }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>공정 실적 등록</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label>투입수량 *</Label>
              <Input
                type="number"
                min={0}
                value={form.input_qty}
                onChange={(e) =>
                  setForm((p) => ({
                    ...p,
                    input_qty: Number(e.target.value),
                  }))
                }
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>산출수량 *</Label>
              <Input
                type="number"
                min={0}
                value={form.output_qty}
                onChange={(e) =>
                  setForm((p) => ({
                    ...p,
                    output_qty: Number(e.target.value),
                  }))
                }
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>불량수량</Label>
              <Input
                type="number"
                min={0}
                value={form.defect_qty}
                onChange={(e) =>
                  setForm((p) => ({
                    ...p,
                    defect_qty: Number(e.target.value),
                  }))
                }
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>시작시간 *</Label>
              <Input
                type="datetime-local"
                value={form.start_time}
                onChange={(e) =>
                  setForm((p) => ({ ...p, start_time: e.target.value }))
                }
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>종료시간 *</Label>
              <Input
                type="datetime-local"
                value={form.end_time}
                onChange={(e) =>
                  setForm((p) => ({ ...p, end_time: e.target.value }))
                }
                required
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>비고</Label>
            <Input
              value={form.condition_notes}
              onChange={(e) =>
                setForm((p) => ({ ...p, condition_notes: e.target.value }))
              }
              placeholder="작업 조건 메모"
            />
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              취소
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? '등록 중...' : '등록'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
