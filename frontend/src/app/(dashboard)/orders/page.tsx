'use client'

import { useEffect, useState } from 'react'
import { Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DataTable } from '@/components/ui/data-table'
import { PageHeader } from '@/components/ui/page-header'
import { StatusBadge } from '@/components/ui/status-badge'
import {
  Dialog,
  DialogContent,
  DialogFooter,
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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useUiStore } from '@/lib/stores/ui-store'
import {
  useOrders,
  useCreateOrder,
  type OrderRead,
  type OrderCreate,
  type OrderItemCreate,
} from '@/lib/hooks/use-orders'
import { useQuery } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'

type CustomerOption = { id: string; name: string }

const STATUS_OPTIONS = [
  { value: 'all', label: '전체' },
  { value: 'received', label: '수주 접수' },
  { value: 'confirmed', label: '확정' },
  { value: 'in_production', label: '생산 중' },
  { value: 'shipped', label: '출하' },
  { value: 'completed', label: '완료' },
  { value: 'cancelled', label: '취소' },
]

const STATUS_LABEL: Record<string, string> = {
  received: '수주 접수',
  confirmed: '확정',
  in_production: '생산 중',
  shipped: '출하',
  completed: '완료',
  cancelled: '취소',
}

export default function OrdersPage() {
  const { setPageTitle } = useUiStore()
  const [statusFilter, setStatusFilter] = useState('all')
  const [dialogOpen, setDialogOpen] = useState(false)

  useEffect(() => { setPageTitle('수주관리') }, [setPageTitle])

  const { data, isLoading } = useOrders(
    statusFilter !== 'all' ? { status: statusFilter } : undefined
  )
  const orders = data?.data ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title="수주관리"
        description="수주 등록, 납기 관리, 생산 진행 현황"
        action={
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4" />
            수주 등록
          </Button>
        }
      />

      <div className="flex items-center gap-3">
        <div className="w-44">
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

      <DataTable<OrderRead>
        isLoading={isLoading}
        data={orders}
        columns={[
          { key: 'order_number', header: '수주번호' },
          {
            key: 'customer_name',
            header: '고객사',
            cell: (row) => row.customer_name ?? '-',
          },
          {
            key: 'status',
            header: '상태',
            cell: (row) => (
              <StatusBadge status={row.status} />
            ),
          },
          { key: 'ordered_date', header: '수주일' },
          {
            key: 'due_date',
            header: '납기일',
            cell: (row) => row.due_date ?? '-',
          },
          {
            key: 'items',
            header: '품목 수',
            cell: (row) => `${row.items.length}개`,
          },
          {
            key: 'total_amount',
            header: '수주금액',
            cell: (row) =>
              row.total_amount
                ? `₩${Number(row.total_amount).toLocaleString()}`
                : '-',
          },
        ]}
      />

      <CreateOrderDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </div>
  )
}

// ─── 수주 등록 다이얼로그 ──────────────────────────────────────────────────────

interface CreateOrderDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const EMPTY_ITEM: OrderItemCreate = {
  material_name: '',
  quantity: 1,
  unit: 'ea',
}

function CreateOrderDialog({ open, onOpenChange }: CreateOrderDialogProps) {
  const { mutate, isPending } = useCreateOrder()
  const [form, setForm] = useState({
    customer_id: '',
    ordered_date: new Date().toISOString().slice(0, 10),
    due_date: '',
    notes: '',
  })
  const [items, setItems] = useState<OrderItemCreate[]>([{ ...EMPTY_ITEM }])

  const { data: customersData } = useQuery<CustomerOption[]>({
    queryKey: ['customers-select'],
    queryFn: () =>
      apiClient
        .get<{ data: CustomerOption[] }>('/api/v1/master/customers', { params: { limit: 100 } })
        .then((r) => r.data.data),
    enabled: open,
  })
  const customers = customersData ?? []

  const addItem = () => setItems((prev) => [...prev, { ...EMPTY_ITEM }])
  const removeItem = (i: number) => setItems((prev) => prev.filter((_, idx) => idx !== i))
  const updateItem = (i: number, field: keyof OrderItemCreate, value: string | number) =>
    setItems((prev) => prev.map((item, idx) => (idx === i ? { ...item, [field]: value } : item)))

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const payload: OrderCreate = {
      customer_id: form.customer_id,
      ordered_date: form.ordered_date,
      due_date: form.due_date || undefined,
      notes: form.notes || undefined,
      items: items.filter((it) => it.material_name.trim()),
    }
    mutate(payload, {
      onSuccess: () => {
        onOpenChange(false)
        setItems([{ ...EMPTY_ITEM }])
        setForm({ customer_id: '', ordered_date: new Date().toISOString().slice(0, 10), due_date: '', notes: '' })
      },
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>수주 등록</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5 col-span-2">
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
                    <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>수주일 *</Label>
              <Input
                type="date"
                value={form.ordered_date}
                onChange={(e) => setForm((p) => ({ ...p, ordered_date: e.target.value }))}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>납기일</Label>
              <Input
                type="date"
                value={form.due_date}
                onChange={(e) => setForm((p) => ({ ...p, due_date: e.target.value }))}
              />
            </div>
          </div>

          {/* 수주 라인 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>수주 품목</Label>
              <Button type="button" variant="ghost" size="sm" onClick={addItem}>
                <Plus className="h-3 w-3 mr-1" /> 행 추가
              </Button>
            </div>
            <div className="rounded-md border divide-y">
              <div className="grid grid-cols-12 gap-2 px-3 py-2 text-xs font-medium text-muted-foreground bg-muted/40">
                <span className="col-span-4">자재명</span>
                <span className="col-span-2">코드</span>
                <span className="col-span-2">수량</span>
                <span className="col-span-2">단위</span>
                <span className="col-span-1">단가</span>
                <span className="col-span-1"></span>
              </div>
              {items.map((item, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 px-3 py-2 items-center">
                  <Input
                    className="col-span-4 h-7 text-sm"
                    placeholder="자재명"
                    value={item.material_name}
                    onChange={(e) => updateItem(i, 'material_name', e.target.value)}
                  />
                  <Input
                    className="col-span-2 h-7 text-sm"
                    placeholder="코드"
                    value={item.material_code ?? ''}
                    onChange={(e) => updateItem(i, 'material_code', e.target.value)}
                  />
                  <Input
                    className="col-span-2 h-7 text-sm"
                    type="number"
                    min={0}
                    step={0.001}
                    value={item.quantity}
                    onChange={(e) => updateItem(i, 'quantity', parseFloat(e.target.value) || 0)}
                  />
                  <Input
                    className="col-span-2 h-7 text-sm"
                    placeholder="ea"
                    value={item.unit}
                    onChange={(e) => updateItem(i, 'unit', e.target.value)}
                  />
                  <Input
                    className="col-span-1 h-7 text-sm"
                    type="number"
                    min={0}
                    placeholder="-"
                    value={item.unit_price ?? ''}
                    onChange={(e) => updateItem(i, 'unit_price', parseFloat(e.target.value) || 0)}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="col-span-1 h-7 w-7"
                    onClick={() => removeItem(i)}
                    disabled={items.length === 1}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
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
