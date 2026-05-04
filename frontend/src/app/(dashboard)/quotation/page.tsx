'use client'

import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { PageHeader } from '@/components/ui/page-header'
import { StatusBadge } from '@/components/ui/status-badge'
import { DataTable } from '@/components/ui/data-table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
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
import { Label } from '@/components/ui/label'
import { useUiStore } from '@/lib/stores/ui-store'
import { useAuth } from '@/lib/hooks/use-auth'
import {
  useQuotations,
  useQuotation,
  useCreateQuotation,
  type QuotationSummary,
} from '@/lib/hooks/use-quotations'
import { useDrawings } from '@/lib/hooks/use-cad'
import {
  useProcessPrices,
  useMaterialPrices,
  useUpsertProcessPrices,
  useUpsertMaterialPrices,
  type ProcessPriceRead,
  type MaterialPriceRead,
  type ProcessPriceUpsert,
  type MaterialPriceUpsert,
} from '@/lib/hooks/use-price-master'
import { QuotationPreview } from '@/components/quotation/quotation-preview'
import { CadUploader } from '@/components/quotation/cad-uploader'
import { DrawingAnalysisCard } from '@/components/quotation/drawing-analysis-card'
import { BomTable } from '@/components/quotation/bom-table'
import { useQuery } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'

type CustomerOption = { id: string; name: string }

const STATUS_LABEL: Record<string, string> = {
  draft:     '초안',
  submitted: '제출됨',
  accepted:  '수락됨',
  rejected:  '거절됨',
  expired:   '만료됨',
}

export default function QuotationPage() {
  const { setPageTitle } = useUiStore()
  const { isAdmin, hasRoles } = useAuth()
  const [tab, setTab] = useState('list')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)

  useEffect(() => { setPageTitle('수주견적 AI') }, [setPageTitle])

  const { data: quotationsData, isLoading } = useQuotations()
  const quotations = quotationsData?.data ?? []

  const { data: selectedQuotation } = useQuotation(selectedId)

  const canManagePrices = isAdmin || hasRoles(['admin', 'production_manager'])

  return (
    <div className="space-y-6">
      <PageHeader
        title="수주견적 AI"
        description="CAD 도면 기반 자동 견적 생성 · GPT-4o Vision 분석"
        action={
          <Button onClick={() => setCreateDialogOpen(true)}>
            <Plus className="h-4 w-4" />
            CAD 견적 생성
          </Button>
        }
      />

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="list">견적 목록</TabsTrigger>
          <TabsTrigger value="cad">CAD 도면</TabsTrigger>
          {selectedId && <TabsTrigger value="detail">견적 상세</TabsTrigger>}
          {canManagePrices && <TabsTrigger value="prices">단가 설정</TabsTrigger>}
        </TabsList>

        {/* 견적 목록 탭 */}
        <TabsContent value="list" className="mt-4">
          <DataTable<QuotationSummary>
            isLoading={isLoading}
            data={quotations}
            columns={[
              { key: 'quotation_number', header: '견적번호' },
              {
                key: 'customer_name',
                header: '고객사',
                cell: (row) => row.customer_name ?? '-',
              },
              {
                key: 'status',
                header: '상태',
                cell: (row) => (
                  <StatusBadge status={row.status} label={STATUS_LABEL[row.status]} />
                ),
              },
              {
                key: 'final_amount',
                header: '최종 금액',
                cell: (row) =>
                  `₩${parseFloat(row.final_amount).toLocaleString('ko-KR', { maximumFractionDigits: 0 })}`,
              },
              {
                key: 'created_at',
                header: '생성일',
                cell: (row) => new Date(row.created_at).toLocaleDateString('ko-KR'),
              },
              {
                key: 'id',
                header: '',
                cell: (row) => (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedId(row.id)
                      setTab('detail')
                    }}
                  >
                    상세
                  </Button>
                ),
              },
            ]}
          />
        </TabsContent>

        {/* CAD 도면 탭 */}
        <TabsContent value="cad" className="mt-4">
          <CadDrawingsTab onQuotationCreated={(id) => { setSelectedId(id); setTab('detail') }} />
        </TabsContent>

        {/* 견적 상세 탭 */}
        {selectedId && (
          <TabsContent value="detail" className="mt-4 space-y-6">
            {selectedQuotation ? (
              <>
                <QuotationPreview quotation={selectedQuotation} />
                {selectedQuotation.status === 'accepted' && (
                  <div className="rounded-lg border bg-white dark:bg-gray-900">
                    <div className="border-b px-4 py-3">
                      <h3 className="font-semibold">BOM (자재 명세서)</h3>
                    </div>
                    <div className="p-4">
                      <BomTable quotationId={selectedQuotation.id} />
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="py-10 text-center text-sm text-gray-500">로딩 중…</div>
            )}
          </TabsContent>
        )}

        {/* 단가 설정 탭 (admin / production_manager) */}
        {canManagePrices && (
          <TabsContent value="prices" className="mt-4">
            <PriceMasterTab />
          </TabsContent>
        )}
      </Tabs>

      <CreateQuotationDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onCreated={(id) => {
          setSelectedId(id)
          setTab('detail')
          setCreateDialogOpen(false)
        }}
      />
    </div>
  )
}

// ─── 단가 설정 탭 (admin / production_manager) ────────────────────────────────

function PriceMasterTab() {
  const { data: processPrices = [], isLoading: loadingProcess } = useProcessPrices()
  const { data: materialPrices = [], isLoading: loadingMaterial } = useMaterialPrices()
  const upsertProcess = useUpsertProcessPrices()
  const upsertMaterial = useUpsertMaterialPrices()

  const [processEdits, setProcessEdits] = useState<Record<string, string>>({})
  const [materialEdits, setMaterialEdits] = useState<Record<string, string>>({})

  const handleSaveProcess = () => {
    const updates: ProcessPriceUpsert[] = processPrices.map((p) => ({
      process_type: p.process_type,
      material_grade: p.material_grade ?? undefined,
      unit_price: parseFloat(processEdits[p.id] ?? p.unit_price),
      price_unit: p.price_unit,
      notes: p.notes ?? undefined,
    }))
    upsertProcess.mutate(updates)
  }

  const handleSaveMaterial = () => {
    const updates: MaterialPriceUpsert[] = materialPrices.map((m) => ({
      material_code: m.material_code,
      material_name: m.material_name,
      price_per_kg: parseFloat(materialEdits[m.id] ?? m.price_per_kg),
      density: parseFloat(m.density),
      notes: m.notes ?? undefined,
    }))
    upsertMaterial.mutate(updates)
  }

  return (
    <div className="space-y-6">
      {/* 공정 단가 */}
      <div className="rounded-lg border bg-white dark:bg-gray-900">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h3 className="font-semibold">공정 단가 마스터</h3>
          <Button size="sm" disabled={upsertProcess.isPending} onClick={handleSaveProcess}>
            {upsertProcess.isPending ? '저장 중…' : '저장'}
          </Button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50 dark:bg-gray-800">
              <tr>
                <th className="px-4 py-2 text-left font-medium">공정</th>
                <th className="px-4 py-2 text-left font-medium">재질 등급</th>
                <th className="px-4 py-2 text-right font-medium">단가</th>
                <th className="px-4 py-2 text-left font-medium">단위</th>
                <th className="px-4 py-2 text-left font-medium">비고</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {loadingProcess ? (
                <tr><td colSpan={5} className="py-6 text-center text-gray-500">로딩 중…</td></tr>
              ) : processPrices.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="px-4 py-2 font-medium">{p.process_type}</td>
                  <td className="px-4 py-2 text-gray-500">{p.material_grade ?? '공통'}</td>
                  <td className="px-4 py-2 text-right">
                    <Input
                      type="number"
                      className="w-28 text-right text-sm"
                      value={processEdits[p.id] ?? p.unit_price}
                      onChange={(e) => setProcessEdits((prev) => ({ ...prev, [p.id]: e.target.value }))}
                    />
                  </td>
                  <td className="px-4 py-2 text-gray-500">{p.price_unit}</td>
                  <td className="px-4 py-2 text-gray-500 text-xs">{p.notes ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 소재 단가 */}
      <div className="rounded-lg border bg-white dark:bg-gray-900">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h3 className="font-semibold">소재 단가 마스터</h3>
          <Button size="sm" disabled={upsertMaterial.isPending} onClick={handleSaveMaterial}>
            {upsertMaterial.isPending ? '저장 중…' : '저장'}
          </Button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50 dark:bg-gray-800">
              <tr>
                <th className="px-4 py-2 text-left font-medium">소재코드</th>
                <th className="px-4 py-2 text-left font-medium">소재명</th>
                <th className="px-4 py-2 text-right font-medium">단가 (원/kg)</th>
                <th className="px-4 py-2 text-right font-medium">밀도 (g/cm³)</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {loadingMaterial ? (
                <tr><td colSpan={4} className="py-6 text-center text-gray-500">로딩 중…</td></tr>
              ) : materialPrices.map((m) => (
                <tr key={m.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="px-4 py-2 font-mono text-xs">{m.material_code}</td>
                  <td className="px-4 py-2">{m.material_name}</td>
                  <td className="px-4 py-2 text-right">
                    <Input
                      type="number"
                      className="w-28 text-right text-sm"
                      value={materialEdits[m.id] ?? m.price_per_kg}
                      onChange={(e) => setMaterialEdits((prev) => ({ ...prev, [m.id]: e.target.value }))}
                    />
                  </td>
                  <td className="px-4 py-2 text-right text-gray-500">{m.density}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ─── CAD 도면 탭 ──────────────────────────────────────────────────────────────

function CadDrawingsTab({ onQuotationCreated }: { onQuotationCreated?: (id: string) => void }) {
  const { data, isLoading } = useDrawings()
  const drawings = data?.data ?? []

  return (
    <div className="space-y-4">
      <div className="max-w-lg">
        <CadUploader />
      </div>

      {isLoading ? (
        <div className="py-8 text-center text-sm text-gray-500">도면 목록 로딩 중…</div>
      ) : drawings.length === 0 ? (
        <div className="py-8 text-center text-sm text-gray-500">등록된 도면이 없습니다.</div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {drawings.map((d) => (
            <DrawingAnalysisCard key={d.id} drawingId={d.id} />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── 견적 생성 다이얼로그 ──────────────────────────────────────────────────────

interface CreateQuotationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated?: (quotationId: string) => void
}

function CreateQuotationDialog({ open, onOpenChange, onCreated }: CreateQuotationDialogProps) {
  const [step, setStep] = useState<'upload' | 'params'>('upload')
  const [drawingId, setDrawingId] = useState<string | null>(null)
  const [customerId, setCustomerId] = useState('')
  const [marginRate, setMarginRate] = useState('0.15')

  const { mutateAsync, isPending } = useCreateQuotation()

  const { data: customersData } = useQuery<CustomerOption[]>({
    queryKey: ['customers-select'],
    queryFn: () =>
      apiClient
        .get<{ data: CustomerOption[] }>('/api/v1/master/customers', { params: { limit: 100 } })
        .then((r) => r.data.data),
    enabled: open,
  })
  const customers = customersData ?? []

  const { data: completedDrawings } = useDrawings({ analysis_status: 'completed' })
  const drawings = completedDrawings?.data ?? []

  const handleCreate = async () => {
    if (!customerId) return
    const q = await mutateAsync({
      customer_id: customerId,
      drawing_id: drawingId ?? undefined,
      margin_rate: parseFloat(marginRate),
    })
    onCreated?.(q.id)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>CAD 견적 생성</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <Tabs value={step} onValueChange={(v) => setStep(v as 'upload' | 'params')}>
            <TabsList className="w-full">
              <TabsTrigger value="upload" className="flex-1">1. 도면 업로드</TabsTrigger>
              <TabsTrigger value="params" className="flex-1">2. 견적 옵션</TabsTrigger>
            </TabsList>

            <TabsContent value="upload" className="mt-3 space-y-3">
              <CadUploader
                customerId={customerId || undefined}
                onDrawingCreated={(id) => {
                  setDrawingId(id)
                  setStep('params')
                }}
              />
              {drawingId && (
                <DrawingAnalysisCard drawingId={drawingId} />
              )}
            </TabsContent>

            <TabsContent value="params" className="mt-3 space-y-3">
              <div className="space-y-1.5">
                <Label>고객사 *</Label>
                <Select value={customerId} onValueChange={setCustomerId}>
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
                <Label>분석 완료 도면 선택</Label>
                <Select
                  value={drawingId ?? ''}
                  onValueChange={setDrawingId}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="도면을 선택하세요" />
                  </SelectTrigger>
                  <SelectContent>
                    {drawings.map((d) => (
                      <SelectItem key={d.id} value={d.id}>
                        {d.drawing_number}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label>마진율 (0.0 ~ 1.0)</Label>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.01}
                  value={marginRate}
                  onChange={(e) => setMarginRate(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                />
              </div>

              <Button
                className="w-full"
                disabled={!customerId || !drawingId || isPending}
                onClick={handleCreate}
              >
                {isPending ? '견적 생성 중…' : '견적 생성'}
              </Button>
            </TabsContent>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  )
}
