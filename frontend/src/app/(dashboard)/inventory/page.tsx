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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useUiStore } from '@/lib/stores/ui-store'
import {
  useQualityInspections,
  useCreateInspection,
  useDefectStats,
  type QualityInspection,
  type QualityInspectionCreate,
} from '@/lib/hooks/use-quality'
import {
  useReceipts,
  useCreateReceipt,
  type ReceiptRead,
  type ReceiptCreate,
} from '@/lib/hooks/use-inbound'
import { formatDateTime } from '@/lib/utils/format'
import { useQuery } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'

type SupplierOption = { id: string; name: string }

export default function InventoryPage() {
  const { setPageTitle } = useUiStore()
  const [tab, setTab] = useState('inventory')
  const [inspDialogOpen, setInspDialogOpen] = useState(false)
  const [receiptDialogOpen, setReceiptDialogOpen] = useState(false)

  useEffect(() => { setPageTitle('입고재고') }, [setPageTitle])

  return (
    <div className="space-y-6">
      <PageHeader
        title="입고재고"
        description="원자재 입고 등록, LOT 생성, 품질 검사 관리"
        action={
          tab === 'quality' ? (
            <Button onClick={() => setInspDialogOpen(true)}>
              <Plus className="h-4 w-4" />
              품질 검사 등록
            </Button>
          ) : tab === 'inventory' ? (
            <Button onClick={() => setReceiptDialogOpen(true)}>
              <Plus className="h-4 w-4" />
              입고 등록
            </Button>
          ) : null
        }
      />

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="inventory">입고 현황</TabsTrigger>
          <TabsTrigger value="quality">품질 검사</TabsTrigger>
        </TabsList>

        <TabsContent value="inventory" className="mt-4">
          <InboundTab />
        </TabsContent>

        <TabsContent value="quality" className="mt-4">
          <QualityInspectionTab />
        </TabsContent>
      </Tabs>

      <CreateReceiptDialog open={receiptDialogOpen} onOpenChange={setReceiptDialogOpen} />
      <CreateInspectionDialog open={inspDialogOpen} onOpenChange={setInspDialogOpen} />
    </div>
  )
}

// ─── 입고 현황 탭 ──────────────────────────────────────────────────────────────

function InboundTab() {
  const { data, isLoading } = useReceipts({ limit: 50 })
  const receipts = data?.data ?? []

  return (
    <DataTable<ReceiptRead>
      isLoading={isLoading}
      data={receipts}
      columns={[
        { key: 'receipt_number', header: '입고번호' },
        {
          key: 'supplier_name',
          header: '공급처',
          cell: (row) => row.supplier_name ?? '-',
        },
        { key: 'material_name', header: '자재명' },
        {
          key: 'quantity',
          header: '수량',
          cell: (row) => `${row.quantity} ${row.unit}`,
        },
        {
          key: 'lot_display_id',
          header: 'LOT',
          cell: (row) =>
            row.lot_display_id ? (
              <span className="font-mono text-xs text-primary">{row.lot_display_id}</span>
            ) : (
              '-'
            ),
        },
        { key: 'received_date', header: '입고일' },
      ]}
    />
  )
}

// ─── 품질 검사 탭 ──────────────────────────────────────────────────────────────

function QualityInspectionTab() {
  const { data, isLoading } = useQualityInspections({ limit: 50 })
  const inspections = data?.data ?? []
  const { data: stats } = useDefectStats({ period_days: 30 })

  return (
    <div className="space-y-4">
      {stats && stats.items.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          {stats.items.slice(0, 3).map((item) => (
            <div key={item.group_key} className="rounded-lg border bg-card p-3">
              <p className="text-xs text-muted-foreground">{item.group_label}</p>
              <p className="text-lg font-bold">{item.avg_defect_rate}%</p>
              <p className="text-xs text-muted-foreground">
                검사 {item.total_inspections}건 · 불합격 {item.fail_count}건
              </p>
            </div>
          ))}
        </div>
      )}

      <DataTable<QualityInspection>
        isLoading={isLoading}
        data={inspections}
        columns={[
          {
            key: 'lot_id',
            header: 'LOT ID',
            cell: (row) => (
              <span className="font-mono text-xs text-primary">{String(row.lot_id).slice(0, 8)}...</span>
            ),
          },
          {
            key: 'inspection_type',
            header: '검사 유형',
            cell: (row) => ({
              incoming: '입고 검사',
              in_process: '공정 검사',
              final: '최종 검사',
              shipment: '출하 검사',
            }[row.inspection_type] ?? row.inspection_type),
          },
          {
            key: 'result',
            header: '결과',
            cell: (row) => (
              <StatusBadge
                status={row.result === 'pass' ? 'completed' : row.result === 'fail' ? 'cancelled' : 'on_hold'}
              />
            ),
          },
          {
            key: 'defect_rate',
            header: '불량률',
            cell: (row) => `${row.defect_rate}%`,
          },
          {
            key: 'inspection_date',
            header: '검사일',
            cell: (row) => formatDateTime(row.inspection_date),
          },
        ]}
      />
    </div>
  )
}

// ─── 입고 등록 다이얼로그 ──────────────────────────────────────────────────────

interface CreateReceiptDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const UNIT_OPTIONS = ['kg', 'sheet', 'piece', 'm', 'ea', 'ton']

function CreateReceiptDialog({ open, onOpenChange }: CreateReceiptDialogProps) {
  const { mutate, isPending } = useCreateReceipt()
  const [form, setForm] = useState<Omit<ReceiptCreate, 'supplier_id'> & { supplier_id: string }>({
    supplier_id: '',
    material_name: '',
    material_code: '',
    quantity: 0,
    unit: 'kg',
    received_date: new Date().toISOString().slice(0, 10),
    notes: '',
  })

  const { data: suppliersData } = useQuery<SupplierOption[]>({
    queryKey: ['suppliers-select'],
    queryFn: () =>
      apiClient
        .get<{ data: SupplierOption[] }>('/api/v1/master/suppliers', { params: { limit: 100 } })
        .then((r) => r.data.data),
    enabled: open,
  })
  const suppliers = suppliersData ?? []

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutate(
      {
        supplier_id: form.supplier_id,
        material_name: form.material_name,
        material_code: form.material_code || undefined,
        quantity: form.quantity,
        unit: form.unit,
        received_date: form.received_date,
        notes: form.notes || undefined,
      },
      { onSuccess: () => onOpenChange(false) }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>입고 등록</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>공급처 *</Label>
            <Select
              value={form.supplier_id}
              onValueChange={(v) => setForm((p) => ({ ...p, supplier_id: v }))}
              required
            >
              <SelectTrigger>
                <SelectValue placeholder="공급처를 선택하세요" />
              </SelectTrigger>
              <SelectContent>
                {suppliers.map((s) => (
                  <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5 col-span-2">
              <Label>자재명 *</Label>
              <Input
                value={form.material_name}
                onChange={(e) => setForm((p) => ({ ...p, material_name: e.target.value }))}
                placeholder="예) SUS304 2T"
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>자재코드</Label>
              <Input
                value={form.material_code}
                onChange={(e) => setForm((p) => ({ ...p, material_code: e.target.value }))}
                placeholder="예) M-001"
              />
            </div>
            <div className="space-y-1.5">
              <Label>입고일 *</Label>
              <Input
                type="date"
                value={form.received_date}
                onChange={(e) => setForm((p) => ({ ...p, received_date: e.target.value }))}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>수량 *</Label>
              <Input
                type="number"
                min={0}
                step={0.001}
                value={form.quantity}
                onChange={(e) => setForm((p) => ({ ...p, quantity: parseFloat(e.target.value) || 0 }))}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>단위</Label>
              <Select
                value={form.unit}
                onValueChange={(v) => setForm((p) => ({ ...p, unit: v }))}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {UNIT_OPTIONS.map((u) => (
                    <SelectItem key={u} value={u}>{u}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
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

          <p className="text-xs text-muted-foreground">
            입고 등록 시 LOT가 자동으로 생성됩니다.
          </p>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              취소
            </Button>
            <Button
              type="submit"
              disabled={isPending || !form.supplier_id || !form.material_name || form.quantity <= 0}
            >
              {isPending ? '등록 중...' : '등록'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ─── 품질 검사 등록 다이얼로그 ────────────────────────────────────────────────

interface CreateInspectionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

function CreateInspectionDialog({ open, onOpenChange }: CreateInspectionDialogProps) {
  const { mutate, isPending } = useCreateInspection()
  const [form, setForm] = useState<QualityInspectionCreate>({
    lot_id: '' as unknown as import('uuid').UUID,
    inspection_type: 'final',
    result: 'pass',
    defect_rate: 0,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutate(form, { onSuccess: () => onOpenChange(false) })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>품질 검사 등록</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>LOT ID *</Label>
            <Input
              value={String(form.lot_id)}
              onChange={(e) => setForm((p) => ({ ...p, lot_id: e.target.value as unknown as import('uuid').UUID }))}
              placeholder="LOT UUID 입력"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>검사 유형</Label>
              <Select
                value={form.inspection_type}
                onValueChange={(v) =>
                  setForm((p) => ({ ...p, inspection_type: v as QualityInspectionCreate['inspection_type'] }))
                }
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="incoming">입고 검사</SelectItem>
                  <SelectItem value="in_process">공정 검사</SelectItem>
                  <SelectItem value="final">최종 검사</SelectItem>
                  <SelectItem value="shipment">출하 검사</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>결과</Label>
              <Select
                value={form.result}
                onValueChange={(v) =>
                  setForm((p) => ({ ...p, result: v as QualityInspectionCreate['result'] }))
                }
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="pass">합격</SelectItem>
                  <SelectItem value="fail">불합격</SelectItem>
                  <SelectItem value="conditional">조건부 합격</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>불량률 (%)</Label>
            <Input
              type="number"
              min={0}
              max={100}
              step={0.1}
              value={form.defect_rate}
              onChange={(e) =>
                setForm((p) => ({ ...p, defect_rate: parseFloat(e.target.value) || 0 }))
              }
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              취소
            </Button>
            <Button type="submit" disabled={isPending || !String(form.lot_id).trim()}>
              {isPending ? '등록 중...' : '등록'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
