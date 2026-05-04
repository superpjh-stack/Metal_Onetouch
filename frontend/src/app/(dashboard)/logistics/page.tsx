'use client'

import { useEffect, useState } from 'react'
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useUiStore } from '@/lib/stores/ui-store'
import {
  useShipments,
  useCreateShipment,
  useUpdateShipmentStatus,
  type Shipment,
} from '@/lib/hooks/use-shipments'
import { X } from 'lucide-react'
import { formatDateTime } from '@/lib/utils/format'
import { useQuery } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'

type CustomerOption = { id: string; name: string }

const STATUS_OPTIONS = [
  { value: 'all', label: '전체' },
  { value: 'pending', label: '출하 대기' },
  { value: 'shipped', label: '배송 중' },
  { value: 'delivered', label: '인수 완료' },
  { value: 'cancelled', label: '취소' },
]

export default function LogisticsPage() {
  const { setPageTitle } = useUiStore()
  const [statusFilter, setStatusFilter] = useState('all')
  const [dialogOpen, setDialogOpen] = useState(false)

  useEffect(() => { setPageTitle('출하물류') }, [setPageTitle])

  const { data, isLoading } = useShipments(
    statusFilter !== 'all' ? { status: statusFilter } : undefined
  )
  const shipments = data?.data ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title="출하물류"
        description="출하 등록, 배송 현황 추적, LOT 출하 묶음 관리"
        action={
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4" />
            출하 등록
          </Button>
        }
      />

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

      <DataTable<Shipment>
        isLoading={isLoading}
        data={shipments}
        columns={[
          { key: 'shipment_number', header: '출하번호' },
          {
            key: 'customer_name',
            header: '고객사',
            cell: (row) => row.customer_name ?? '-',
          },
          {
            key: 'status',
            header: '상태',
            cell: (row) => <StatusBadge status={row.status} />,
          },
          {
            key: 'planned_date',
            header: '계획 출하일',
            cell: (row) => row.planned_date ?? '-',
          },
          {
            key: 'lots',
            header: 'LOT 수',
            cell: (row) => `${row.lots.length}개`,
          },
          {
            key: 'shipped_date',
            header: '실출하일',
            cell: (row) =>
              row.shipped_date ? formatDateTime(row.shipped_date) : '-',
          },
        ]}
      />

      <CreateShipmentDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </div>
  )
}

interface CreateShipmentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

function CreateShipmentDialog({ open, onOpenChange }: CreateShipmentDialogProps) {
  const { mutate, isPending } = useCreateShipment()
  const [form, setForm] = useState({
    customer_id: '',
    planned_date: '',
    notes: '',
  })
  const [lotRows, setLotRows] = useState<{ lot_id: string; qty: string }[]>([])

  const addLotRow = () => setLotRows((prev) => [...prev, { lot_id: '', qty: '1' }])
  const removeLotRow = (i: number) => setLotRows((prev) => prev.filter((_, idx) => idx !== i))
  const updateLotRow = (i: number, field: 'lot_id' | 'qty', value: string) =>
    setLotRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)))

  const { data: customersData } = useQuery<CustomerOption[]>({
    queryKey: ['customers-select'],
    queryFn: () =>
      apiClient
        .get<{ data: CustomerOption[] }>('/api/v1/master/customers', {
          params: { limit: 100 },
        })
        .then((r) => r.data.data),
    enabled: open,
  })
  const customers = customersData ?? []

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutate(
      {
        customer_id: form.customer_id,
        planned_date: form.planned_date || undefined,
        notes: form.notes || undefined,
        lots: lotRows
          .filter((r) => r.lot_id.trim())
          .map((r) => ({ lot_id: r.lot_id, qty: parseFloat(r.qty) || 1 })),
      },
      {
        onSuccess: () => {
          onOpenChange(false)
          setLotRows([])
        },
      }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>출하 등록</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>고객사 *</Label>
            <Select
              value={form.customer_id}
              onValueChange={(v) => setForm((p) => ({ ...p, customer_id: v }))}
              required
            >
              <SelectTrigger>
                <SelectValue placeholder="고객사를 선택하세요" />
              </SelectTrigger>
              <SelectContent>
                {customers.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>계획 출하일</Label>
            <Input
              type="date"
              value={form.planned_date}
              onChange={(e) => setForm((p) => ({ ...p, planned_date: e.target.value }))}
            />
          </div>
          {/* LOT 번들 섹션 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>LOT 번들 (선택)</Label>
              <Button type="button" variant="ghost" size="sm" onClick={addLotRow}>
                <Plus className="h-3 w-3 mr-1" /> 추가
              </Button>
            </div>
            {lotRows.map((row, i) => (
              <div key={i} className="flex gap-2 items-center">
                <Input
                  className="flex-1"
                  placeholder="LOT UUID"
                  value={row.lot_id}
                  onChange={(e) => updateLotRow(i, 'lot_id', e.target.value)}
                />
                <Input
                  type="number"
                  min={0}
                  step={0.001}
                  className="w-24"
                  placeholder="수량"
                  value={row.qty}
                  onChange={(e) => updateLotRow(i, 'qty', e.target.value)}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removeLotRow(i)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>

          <div className="space-y-1.5">
            <Label>비고</Label>
            <Input
              value={form.notes}
              onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))}
              placeholder="특이사항 입력"
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              취소
            </Button>
            <Button type="submit" disabled={isPending || !form.customer_id}>
              {isPending ? '등록 중...' : '등록'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
