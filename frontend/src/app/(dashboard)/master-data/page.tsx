'use client'

import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DataTable } from '@/components/ui/data-table'
import { StatusBadge } from '@/components/ui/status-badge'
import { PageHeader } from '@/components/ui/page-header'
import { useUiStore } from '@/lib/stores/ui-store'
import {
  useSuppliers,
  useCustomers,
  useMaterials,
  useProcessTypes,
  useEquipment,
  useCreateSupplier,
  useCreateCustomer,
  useCreateMaterial,
  useCreateProcessType,
  useCreateEquipment,
} from '@/lib/hooks/use-master-data'
import type {
  Supplier,
  Customer,
  RawMaterial,
  ProcessTypeRecord,
  EquipmentRecord,
} from '@/types'

// ============================================================
// 기준정보 관리 페이지 (탭 구조)
// ============================================================

type ActiveTab =
  | 'suppliers'
  | 'customers'
  | 'materials'
  | 'processes'
  | 'equipment'

export default function MasterDataPage() {
  const { setPageTitle } = useUiStore()
  const [activeTab, setActiveTab] = useState<ActiveTab>('suppliers')
  const [dialogOpen, setDialogOpen] = useState(false)

  useEffect(() => {
    setPageTitle('기준정보 관리')
  }, [setPageTitle])

  const registerLabel: Record<ActiveTab, string> = {
    suppliers: '공급업체 등록',
    customers: '고객사 등록',
    materials: '원자재 등록',
    processes: '공정유형 등록',
    equipment: '설비 등록',
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="기준정보 관리"
        description="공급업체, 고객사, 원자재, 공정유형, 설비 마스터 데이터를 관리합니다."
        action={
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4" />
            {registerLabel[activeTab]}
          </Button>
        }
      />

      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as ActiveTab)}
      >
        <TabsList>
          <TabsTrigger value="suppliers">공급업체</TabsTrigger>
          <TabsTrigger value="customers">고객사</TabsTrigger>
          <TabsTrigger value="materials">원자재</TabsTrigger>
          <TabsTrigger value="processes">공정유형</TabsTrigger>
          <TabsTrigger value="equipment">설비</TabsTrigger>
        </TabsList>

        <TabsContent value="suppliers">
          <SupplierTab />
        </TabsContent>
        <TabsContent value="customers">
          <CustomerTab />
        </TabsContent>
        <TabsContent value="materials">
          <MaterialTab />
        </TabsContent>
        <TabsContent value="processes">
          <ProcessTypeTab />
        </TabsContent>
        <TabsContent value="equipment">
          <EquipmentTab />
        </TabsContent>
      </Tabs>

      {/* 등록 다이얼로그 — 탭별 폼 */}
      {activeTab === 'suppliers' && (
        <SupplierDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
        />
      )}
      {activeTab === 'customers' && (
        <CustomerDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
        />
      )}
      {activeTab === 'materials' && (
        <MaterialDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
        />
      )}
      {activeTab === 'processes' && (
        <ProcessTypeDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
        />
      )}
      {activeTab === 'equipment' && (
        <EquipmentDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
        />
      )}
    </div>
  )
}

// ============================================================
// 공급업체 탭
// ============================================================

function SupplierTab() {
  const { data, isLoading } = useSuppliers()
  const suppliers = data?.data ?? []

  return (
    <DataTable<Supplier>
      isLoading={isLoading}
      data={suppliers}
      columns={[
        { key: 'supplier_code', header: '코드' },
        { key: 'name', header: '이름' },
        {
          key: 'contact_person',
          header: '담당자',
          cell: (row) => row.contact_person ?? '-',
        },
        {
          key: 'phone',
          header: '전화',
          cell: (row) => row.phone ?? '-',
        },
        {
          key: 'grade',
          header: '등급',
          cell: (row) => <StatusBadge status={row.grade} />,
        },
        {
          key: 'is_active',
          header: '상태',
          cell: (row) => (
            <StatusBadge
              status={row.is_active ? 'completed' : 'cancelled'}
              label={row.is_active ? '활성' : '비활성'}
            />
          ),
        },
      ]}
    />
  )
}

// ============================================================
// 고객사 탭
// ============================================================

function CustomerTab() {
  const { data, isLoading } = useCustomers()
  const customers = data?.data ?? []

  return (
    <DataTable<Customer>
      isLoading={isLoading}
      data={customers}
      columns={[
        { key: 'customer_code', header: '코드' },
        { key: 'name', header: '이름' },
        {
          key: 'contact_person',
          header: '담당자',
          cell: (row) => row.contact_person ?? '-',
        },
        {
          key: 'email',
          header: '이메일',
          cell: (row) => row.email ?? '-',
        },
        {
          key: 'is_active',
          header: '상태',
          cell: (row) => (
            <StatusBadge
              status={row.is_active ? 'completed' : 'cancelled'}
              label={row.is_active ? '활성' : '비활성'}
            />
          ),
        },
      ]}
    />
  )
}

// ============================================================
// 원자재 탭
// ============================================================

function MaterialTab() {
  const { data, isLoading } = useMaterials()
  const materials = data?.data ?? []

  return (
    <DataTable<RawMaterial>
      isLoading={isLoading}
      data={materials}
      columns={[
        { key: 'material_code', header: '자재코드' },
        { key: 'name', header: '이름' },
        { key: 'category', header: '분류' },
        {
          key: 'spec',
          header: '규격',
          cell: (row) => row.spec ?? '-',
        },
        {
          key: 'stock_qty',
          header: '재고수량',
          cell: (row) =>
            row.stock_qty.toLocaleString('ko-KR'),
        },
        { key: 'unit', header: '단위' },
        {
          key: 'supplier_name',
          header: '공급업체',
          cell: (row) => row.supplier_name ?? '-',
        },
      ]}
    />
  )
}

// ============================================================
// 공정유형 탭
// ============================================================

function ProcessTypeTab() {
  const { data, isLoading } = useProcessTypes()
  const processTypes = data?.data ?? []

  return (
    <DataTable<ProcessTypeRecord>
      isLoading={isLoading}
      data={processTypes}
      columns={[
        { key: 'process_code', header: '공정코드' },
        { key: 'name', header: '이름' },
        { key: 'process_type', header: '공정유형' },
        {
          key: 'std_time_min',
          header: '표준작업시간(분)',
          cell: (row) =>
            row.std_time_min != null ? `${row.std_time_min}분` : '-',
        },
        {
          key: 'is_active',
          header: '상태',
          cell: (row) => (
            <StatusBadge
              status={row.is_active ? 'completed' : 'cancelled'}
              label={row.is_active ? '활성' : '비활성'}
            />
          ),
        },
      ]}
    />
  )
}

// ============================================================
// 설비 탭
// ============================================================

function EquipmentTab() {
  const { data, isLoading } = useEquipment()
  const equipment = data?.data ?? []

  return (
    <DataTable<EquipmentRecord>
      isLoading={isLoading}
      data={equipment}
      columns={[
        { key: 'equipment_code', header: '설비코드' },
        { key: 'name', header: '이름' },
        {
          key: 'process_name',
          header: '공정유형',
          cell: (row) => row.process_name ?? '-',
        },
        {
          key: 'manufacturer',
          header: '제조사',
          cell: (row) => row.manufacturer ?? '-',
        },
        {
          key: 'status',
          header: '상태',
          cell: (row) => <StatusBadge status={row.status} />,
        },
        {
          key: 'location',
          header: '위치',
          cell: (row) => row.location ?? '-',
        },
      ]}
    />
  )
}

// ============================================================
// 등록 다이얼로그들
// ============================================================

interface DialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

function SupplierDialog({ open, onOpenChange }: DialogProps) {
  const { mutate, isPending } = useCreateSupplier()
  const [form, setForm] = useState({
    supplier_code: '',
    name: '',
    contact_person: '',
    phone: '',
    grade: 'B' as Supplier['grade'],
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutate(
      { ...form, is_active: true },
      { onSuccess: () => onOpenChange(false) }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>공급업체 등록</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField label="공급업체 코드 *">
            <Input
              value={form.supplier_code}
              onChange={(e) =>
                setForm((p) => ({ ...p, supplier_code: e.target.value }))
              }
              placeholder="SUP-001"
              required
            />
          </FormField>
          <FormField label="업체명 *">
            <Input
              value={form.name}
              onChange={(e) =>
                setForm((p) => ({ ...p, name: e.target.value }))
              }
              placeholder="(주)한국금속"
              required
            />
          </FormField>
          <FormField label="담당자">
            <Input
              value={form.contact_person}
              onChange={(e) =>
                setForm((p) => ({ ...p, contact_person: e.target.value }))
              }
              placeholder="홍길동"
            />
          </FormField>
          <FormField label="전화번호">
            <Input
              value={form.phone}
              onChange={(e) =>
                setForm((p) => ({ ...p, phone: e.target.value }))
              }
              placeholder="02-1234-5678"
            />
          </FormField>
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

function CustomerDialog({ open, onOpenChange }: DialogProps) {
  const { mutate, isPending } = useCreateCustomer()
  const [form, setForm] = useState({
    customer_code: '',
    name: '',
    contact_person: '',
    email: '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutate(
      { ...form, is_active: true },
      { onSuccess: () => onOpenChange(false) }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>고객사 등록</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField label="고객사 코드 *">
            <Input
              value={form.customer_code}
              onChange={(e) =>
                setForm((p) => ({ ...p, customer_code: e.target.value }))
              }
              placeholder="CUS-001"
              required
            />
          </FormField>
          <FormField label="고객사명 *">
            <Input
              value={form.name}
              onChange={(e) =>
                setForm((p) => ({ ...p, name: e.target.value }))
              }
              placeholder="(주)ABC산업"
              required
            />
          </FormField>
          <FormField label="담당자">
            <Input
              value={form.contact_person}
              onChange={(e) =>
                setForm((p) => ({ ...p, contact_person: e.target.value }))
              }
              placeholder="김영수"
            />
          </FormField>
          <FormField label="이메일">
            <Input
              type="email"
              value={form.email}
              onChange={(e) =>
                setForm((p) => ({ ...p, email: e.target.value }))
              }
              placeholder="contact@abc.co.kr"
            />
          </FormField>
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

function MaterialDialog({ open, onOpenChange }: DialogProps) {
  const { mutate, isPending } = useCreateMaterial()
  const [form, setForm] = useState({
    material_code: '',
    name: '',
    category: '',
    unit: 'kg',
    stock_qty: 0,
    min_stock_qty: 0,
    lead_time_days: 3,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutate(
      { ...form, is_active: true },
      { onSuccess: () => onOpenChange(false) }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>원자재 등록</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField label="자재코드 *">
            <Input
              value={form.material_code}
              onChange={(e) =>
                setForm((p) => ({ ...p, material_code: e.target.value }))
              }
              placeholder="MAT-001"
              required
            />
          </FormField>
          <FormField label="자재명 *">
            <Input
              value={form.name}
              onChange={(e) =>
                setForm((p) => ({ ...p, name: e.target.value }))
              }
              placeholder="SUS304 판재"
              required
            />
          </FormField>
          <FormField label="분류 *">
            <Input
              value={form.category}
              onChange={(e) =>
                setForm((p) => ({ ...p, category: e.target.value }))
              }
              placeholder="스테인리스"
              required
            />
          </FormField>
          <FormField label="단위">
            <Input
              value={form.unit}
              onChange={(e) =>
                setForm((p) => ({ ...p, unit: e.target.value }))
              }
              placeholder="kg"
            />
          </FormField>
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

function ProcessTypeDialog({ open, onOpenChange }: DialogProps) {
  const { mutate, isPending } = useCreateProcessType()
  const [form, setForm] = useState({
    process_code: '',
    name: '',
    process_type: '',
    std_time_min: 60,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutate(
      { ...form, is_active: true },
      { onSuccess: () => onOpenChange(false) }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>공정유형 등록</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField label="공정코드 *">
            <Input
              value={form.process_code}
              onChange={(e) =>
                setForm((p) => ({ ...p, process_code: e.target.value }))
              }
              placeholder="PROC-001"
              required
            />
          </FormField>
          <FormField label="공정명 *">
            <Input
              value={form.name}
              onChange={(e) =>
                setForm((p) => ({ ...p, name: e.target.value }))
              }
              placeholder="레이저 절단"
              required
            />
          </FormField>
          <FormField label="공정유형 *">
            <Input
              value={form.process_type}
              onChange={(e) =>
                setForm((p) => ({ ...p, process_type: e.target.value }))
              }
              placeholder="cutting"
              required
            />
          </FormField>
          <FormField label="표준작업시간(분)">
            <Input
              type="number"
              value={form.std_time_min}
              onChange={(e) =>
                setForm((p) => ({
                  ...p,
                  std_time_min: Number(e.target.value),
                }))
              }
              min={1}
            />
          </FormField>
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

function EquipmentDialog({ open, onOpenChange }: DialogProps) {
  const { mutate, isPending } = useCreateEquipment()
  const [form, setForm] = useState({
    equipment_code: '',
    name: '',
    manufacturer: '',
    location: '',
    status: 'idle' as EquipmentRecord['status'],
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutate(
      { ...form, is_active: true },
      { onSuccess: () => onOpenChange(false) }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>설비 등록</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField label="설비코드 *">
            <Input
              value={form.equipment_code}
              onChange={(e) =>
                setForm((p) => ({ ...p, equipment_code: e.target.value }))
              }
              placeholder="EQP-001"
              required
            />
          </FormField>
          <FormField label="설비명 *">
            <Input
              value={form.name}
              onChange={(e) =>
                setForm((p) => ({ ...p, name: e.target.value }))
              }
              placeholder="레이저 절단기 #1"
              required
            />
          </FormField>
          <FormField label="제조사">
            <Input
              value={form.manufacturer}
              onChange={(e) =>
                setForm((p) => ({ ...p, manufacturer: e.target.value }))
              }
              placeholder="TRUMPF"
            />
          </FormField>
          <FormField label="위치">
            <Input
              value={form.location}
              onChange={(e) =>
                setForm((p) => ({ ...p, location: e.target.value }))
              }
              placeholder="A동 1라인"
            />
          </FormField>
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

// ============================================================
// 공통 폼 필드 래퍼
// ============================================================

function FormField({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  )
}
