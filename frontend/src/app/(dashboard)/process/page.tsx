'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DataTable } from '@/components/ui/data-table'
import { StatusBadge } from '@/components/ui/status-badge'
import { PageHeader } from '@/components/ui/page-header'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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
  useWorkOrders,
  useCreateWorkOrder,
} from '@/lib/hooks/use-work-orders'
import { useProcessTypes } from '@/lib/hooks/use-master-data'
import apiClient from '@/lib/api/client'
import { formatDateTime } from '@/lib/utils/format'
import type { WorkOrder } from '@/types'

type LotOption = { id: string; lot_id: string; product_name?: string; raw_material_name?: string }

// ============================================================
// 공정관리 페이지 (작업지시 목록)
// ============================================================

const STATUS_OPTIONS = [
  { value: 'all', label: '전체' },
  { value: 'pending', label: '대기' },
  { value: 'in_progress', label: '진행 중' },
  { value: 'completed', label: '완료' },
  { value: 'on_hold', label: '보류' },
  { value: 'cancelled', label: '취소' },
]

export default function ProcessPage() {
  const router = useRouter()
  const { setPageTitle } = useUiStore()
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [dialogOpen, setDialogOpen] = useState(false)

  useEffect(() => {
    setPageTitle('공정관리')
  }, [setPageTitle])

  const { data, isLoading } = useWorkOrders(
    statusFilter !== 'all' ? { status: statusFilter } : undefined
  )
  const workOrders = data?.data ?? []

  // 진도율 계산: output_qty / input_qty * 100
  function calcProgress(wo: WorkOrder): string {
    if (!wo.input_qty || wo.input_qty === 0) return '-'
    const pct = Math.round(((wo.output_qty ?? 0) / wo.input_qty) * 100)
    return `${pct}%`
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="공정관리"
        description="작업지시 생성, 진행 현황 추적, 공정 실적 관리"
        action={
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4" />
            작업지시 등록
          </Button>
        }
      />

      {/* 필터 행 */}
      <div className="flex items-center gap-3">
        <div className="w-40">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger>
              <SelectValue placeholder="상태 선택" />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <DataTable<WorkOrder>
        isLoading={isLoading}
        data={workOrders}
        onRowClick={(wo) => router.push(`/process/${wo.id}`)}
        columns={[
          { key: 'wo_number', header: 'WO번호' },
          {
            key: 'lot_display_id',
            header: 'LOT ID',
            cell: (row) => (
              <span className="font-mono text-xs text-primary">
                {row.lot_display_id ?? row.lot_id}
              </span>
            ),
          },
          {
            key: 'process_name',
            header: '공정',
            cell: (row) => row.process_name ?? '-',
          },
          {
            key: 'assigned_name',
            header: '담당자',
            cell: (row) => row.assigned_name ?? '-',
          },
          {
            key: 'planned_start',
            header: '계획시작',
            cell: (row) =>
              row.planned_start ? formatDateTime(row.planned_start) : '-',
          },
          {
            key: 'status',
            header: '상태',
            cell: (row) => <StatusBadge status={row.status} />,
          },
          {
            key: 'output_qty',
            header: '진도율',
            cell: (row) => calcProgress(row),
          },
        ]}
      />

      <CreateWorkOrderDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </div>
  )
}

// ============================================================
// 작업지시 등록 다이얼로그
// ============================================================

interface CreateWorkOrderDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

function CreateWorkOrderDialog({
  open,
  onOpenChange,
}: CreateWorkOrderDialogProps) {
  const { mutate, isPending } = useCreateWorkOrder()
  const [form, setForm] = useState({
    lot_id: '',
    process_id: '',
    planned_start: '',
    planned_end: '',
  })

  const { data: lotsData } = useQuery<LotOption[]>({
    queryKey: ['lots-select'],
    queryFn: () =>
      apiClient
        .get<{ data: LotOption[] }>('/api/v1/lots', { params: { limit: 100 } })
        .then((r) => r.data.data),
    enabled: open,
  })
  const lots = lotsData ?? []

  const { data: processTypesData } = useProcessTypes()
  const processes = processTypesData?.data ?? []

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutate(
      {
        lot_id: form.lot_id,
        process_id: form.process_id,
        planned_start: form.planned_start || undefined,
        planned_end: form.planned_end || undefined,
      },
      { onSuccess: () => onOpenChange(false) }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>작업지시 등록</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>LOT 선택 *</Label>
            <Select
              value={form.lot_id}
              onValueChange={(v) => setForm((p) => ({ ...p, lot_id: v }))}
              required
            >
              <SelectTrigger>
                <SelectValue placeholder="LOT를 선택하세요" />
              </SelectTrigger>
              <SelectContent>
                {lots.map((lot) => (
                  <SelectItem key={lot.id} value={lot.id}>
                    {lot.lot_id}
                    {lot.product_name
                      ? ` — ${lot.product_name}`
                      : lot.raw_material_name
                      ? ` — ${lot.raw_material_name}`
                      : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>공정 선택 *</Label>
            <Select
              value={form.process_id}
              onValueChange={(v) => setForm((p) => ({ ...p, process_id: v }))}
              required
            >
              <SelectTrigger>
                <SelectValue placeholder="공정을 선택하세요" />
              </SelectTrigger>
              <SelectContent>
                {processes.map((pt) => (
                  <SelectItem key={pt.id} value={pt.id}>
                    {pt.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>계획 시작</Label>
              <Input
                type="datetime-local"
                value={form.planned_start}
                onChange={(e) =>
                  setForm((p) => ({ ...p, planned_start: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label>계획 종료</Label>
              <Input
                type="datetime-local"
                value={form.planned_end}
                onChange={(e) =>
                  setForm((p) => ({ ...p, planned_end: e.target.value }))
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              취소
            </Button>
            <Button
              type="submit"
              disabled={isPending || !form.lot_id || !form.process_id}
            >
              {isPending ? '등록 중...' : '등록'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
