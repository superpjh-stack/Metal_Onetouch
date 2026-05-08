'use client'

import { useEffect, useState } from 'react'
import { Plus, X, CheckCircle2, Truck, Package } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DataTable } from '@/components/ui/data-table'
import { StatusBadge } from '@/components/ui/status-badge'
import { PageHeader } from '@/components/ui/page-header'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
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

const STATUS_LABEL: Record<string, string> = {
  pending: '출하 대기',
  shipped: '배송 중',
  delivered: '인수 완료',
  cancelled: '취소',
}

// ============================================================
// 출하물류 메인 페이지
// ============================================================

export default function ShipmentPage() {
  const { setPageTitle } = useUiStore()
  const [tab, setTab] = useState('list')
  const [statusFilter, setStatusFilter] = useState('all')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [statusDialogOpen, setStatusDialogOpen] = useState(false)
  const [selectedShipment, setSelectedShipment] = useState<Shipment | null>(null)

  useEffect(() => {
    setPageTitle('출하물류')
  }, [setPageTitle])

  const { data, isLoading } = useShipments(
    statusFilter !== 'all' ? { status: statusFilter } : undefined
  )
  const shipments = data?.data ?? []

  const pendingCount = shipments.filter((s) => s.status === 'pending').length
  const shippedCount = shipments.filter((s) => s.status === 'shipped').length
  const deliveredCount = shipments.filter((s) => s.status === 'delivered').length

  const handleStatusUpdate = (shipment: Shipment) => {
    setSelectedShipment(shipment)
    setStatusDialogOpen(true)
  }

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

      {/* 요약 카드 */}
      <div className="grid grid-cols-3 gap-4">
        <SummaryCard label="출하 대기" value={pendingCount} icon={Package} color="yellow" />
        <SummaryCard label="배송 중" value={shippedCount} icon={Truck} color="blue" />
        <SummaryCard label="인수 완료" value={deliveredCount} icon={CheckCircle2} color="green" />
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="list">출하 목록</TabsTrigger>
            <TabsTrigger value="pending">대기 목록</TabsTrigger>
          </TabsList>

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

        <TabsContent value="list" className="mt-4">
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
              {
                key: 'delivered_date',
                header: '인수완료일',
                cell: (row) =>
                  row.delivered_date ? formatDateTime(row.delivered_date) : '-',
              },
              {
                key: 'id',
                header: '상태변경',
                cell: (row) =>
                  row.status !== 'delivered' && row.status !== 'cancelled' ? (
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleStatusUpdate(row)
                      }}
                    >
                      상태 변경
                    </Button>
                  ) : null,
              },
            ]}
          />
        </TabsContent>

        <TabsContent value="pending" className="mt-4">
          <PendingShipmentTab onStatusUpdate={handleStatusUpdate} />
        </TabsContent>
      </Tabs>

      <CreateShipmentDialog open={dialogOpen} onOpenChange={setDialogOpen} />

      {selectedShipment && (
        <UpdateStatusDialog
          open={statusDialogOpen}
          onOpenChange={setStatusDialogOpen}
          shipment={selectedShipment}
        />
      )}
    </div>
  )
}

// ============================================================
// 요약 카드
// ============================================================

function SummaryCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string
  value: number
  icon: React.ComponentType<{ className?: string }>
  color: 'yellow' | 'blue' | 'green'
}) {
  const colorMap = {
    yellow: 'bg-yellow-50 text-yellow-700 dark:bg-yellow-950/30 dark:text-yellow-400',
    blue: 'bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-400',
    green: 'bg-green-50 text-green-700 dark:bg-green-950/30 dark:text-green-400',
  }
  return (
    <div className="rounded-xl border bg-card p-4 flex items-center gap-4">
      <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${colorMap[color]}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-2xl font-bold text-foreground">{value}<span className="text-sm font-normal text-muted-foreground ml-1">건</span></p>
      </div>
    </div>
  )
}

// ============================================================
// 대기 목록 탭
// ============================================================

function PendingShipmentTab({ onStatusUpdate }: { onStatusUpdate: (s: Shipment) => void }) {
  const { data, isLoading } = useShipments({ status: 'pending' })
  const pending = data?.data ?? []

  return (
    <DataTable<Shipment>
      isLoading={isLoading}
      data={pending}
      columns={[
        { key: 'shipment_number', header: '출하번호' },
        {
          key: 'customer_name',
          header: '고객사',
          cell: (row) => row.customer_name ?? '-',
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
          key: 'id',
          header: '처리',
          cell: (row) => (
            <Button
              size="sm"
              className="h-7 text-xs"
              onClick={(e) => {
                e.stopPropagation()
                onStatusUpdate(row)
              }}
            >
              <Truck className="mr-1 h-3.5 w-3.5" />
              출하 처리
            </Button>
          ),
        },
      ]}
    />
  )
}

// ============================================================
// 출하 등록 다이얼로그
// ============================================================

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
          setForm({ customer_id: '', planned_date: '', notes: '' })
          setLotRows([])
        },
      }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
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

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>LOT 번들 (선택)</Label>
              <Button type="button" variant="ghost" size="sm" onClick={addLotRow}>
                <Plus className="h-3 w-3 mr-1" /> LOT 추가
              </Button>
            </div>
            {lotRows.length > 0 && (
              <div className="rounded-md border divide-y">
                <div className="grid grid-cols-12 gap-2 px-3 py-2 text-xs font-medium text-muted-foreground bg-muted/40">
                  <span className="col-span-8">LOT UUID</span>
                  <span className="col-span-3">수량</span>
                  <span className="col-span-1" />
                </div>
                {lotRows.map((row, i) => (
                  <div key={i} className="grid grid-cols-12 gap-2 px-3 py-2 items-center">
                    <Input
                      className="col-span-8 h-7 text-sm font-mono"
                      placeholder="LOT UUID"
                      value={row.lot_id}
                      onChange={(e) => updateLotRow(i, 'lot_id', e.target.value)}
                    />
                    <Input
                      type="number"
                      min={0}
                      step={0.001}
                      className="col-span-3 h-7 text-sm"
                      placeholder="수량"
                      value={row.qty}
                      onChange={(e) => updateLotRow(i, 'qty', e.target.value)}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="col-span-1 h-7 w-7"
                      onClick={() => removeLotRow(i)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
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

// ============================================================
// 상태 변경 다이얼로그
// ============================================================

interface UpdateStatusDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  shipment: Shipment
}

const NEXT_STATUS_OPTIONS: Record<string, { value: string; label: string }[]> = {
  pending: [
    { value: 'shipped', label: '배송 중으로 변경' },
    { value: 'cancelled', label: '취소' },
  ],
  shipped: [
    { value: 'delivered', label: '인수 완료로 변경' },
    { value: 'cancelled', label: '취소' },
  ],
}

function UpdateStatusDialog({ open, onOpenChange, shipment }: UpdateStatusDialogProps) {
  const { mutate, isPending } = useUpdateShipmentStatus()
  const [status, setStatus] = useState<string>('')
  const [notes, setNotes] = useState('')

  const options = NEXT_STATUS_OPTIONS[shipment.status] ?? []

  useEffect(() => {
    if (open) {
      setStatus(options[0]?.value ?? '')
      setNotes('')
    }
  }, [open, shipment.status])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!status) return
    mutate(
      {
        shipmentId: shipment.id,
        body: {
          status: status as 'shipped' | 'delivered' | 'cancelled',
          notes: notes || undefined,
        },
      },
      { onSuccess: () => onOpenChange(false) }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>출하 상태 변경</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="rounded-lg border bg-muted/30 p-3 text-sm">
            <p className="font-medium">{shipment.shipment_number}</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {shipment.customer_name ?? '-'} · 현재: <span className="font-medium">{STATUS_LABEL[shipment.status]}</span>
            </p>
          </div>

          <div className="space-y-1.5">
            <Label>변경할 상태</Label>
            <Select value={status} onValueChange={setStatus} required>
              <SelectTrigger>
                <SelectValue placeholder="상태 선택" />
              </SelectTrigger>
              <SelectContent>
                {options.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>비고</Label>
            <Input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="상태 변경 사유 (선택)"
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              취소
            </Button>
            <Button type="submit" disabled={isPending || !status}>
              {isPending ? '처리 중...' : '변경'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
