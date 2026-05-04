'use client'

import { Button } from '@/components/ui/button'
import { useBom, useGenerateBom, useExportBom } from '@/lib/hooks/use-bom'
import { Download, RefreshCw } from 'lucide-react'

interface BomTableProps {
  quotationId: string
}

export function BomTable({ quotationId }: BomTableProps) {
  const { data: bom, isLoading } = useBom(quotationId)
  const generate = useGenerateBom(quotationId)
  const exportBom = useExportBom()

  if (isLoading) {
    return <div className="py-6 text-center text-sm text-muted-foreground">BOM 로딩 중…</div>
  }

  if (!bom) {
    return (
      <div className="flex flex-col items-center gap-3 py-10">
        <p className="text-sm text-muted-foreground">BOM이 아직 생성되지 않았습니다.</p>
        <Button
          size="sm"
          disabled={generate.isPending}
          onClick={() => generate.mutate()}
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          {generate.isPending ? 'BOM 생성 중…' : 'BOM 자동 생성'}
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Rev. {bom.revision} · 총 중량:{' '}
          <span className="font-semibold text-foreground">
            {bom.total_weight_kg.toFixed(3)} kg
          </span>
          {bom.notes && <span className="ml-2">· {bom.notes}</span>}
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={generate.isPending}
            onClick={() => generate.mutate()}
          >
            <RefreshCw className="mr-2 h-3.5 w-3.5" />
            재생성
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={exportBom.isPending}
            onClick={() => exportBom.mutate(bom.id)}
          >
            <Download className="mr-2 h-3.5 w-3.5" />
            Excel
          </Button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/50">
            <tr>
              <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">#</th>
              <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">소재코드</th>
              <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">규격</th>
              <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">수량</th>
              <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">단위</th>
              <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">단위중량(kg)</th>
              <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">총중량(kg)</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {bom.items.map((item) => (
              <tr key={item.id} className="hover:bg-muted/30">
                <td className="px-4 py-2.5 text-muted-foreground">{item.sort_order}</td>
                <td className="px-4 py-2.5 font-mono text-xs">{item.material_code}</td>
                <td className="px-4 py-2.5">{item.specification}</td>
                <td className="px-4 py-2.5 text-right">{item.quantity}</td>
                <td className="px-4 py-2.5 text-muted-foreground">{item.unit}</td>
                <td className="px-4 py-2.5 text-right">
                  {item.unit_weight_kg != null ? item.unit_weight_kg.toFixed(4) : '-'}
                </td>
                <td className="px-4 py-2.5 text-right font-medium">
                  {item.total_weight_kg.toFixed(3)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot className="border-t bg-muted/50">
            <tr>
              <td colSpan={6} className="px-4 py-2.5 text-right text-sm font-semibold">합계</td>
              <td className="px-4 py-2.5 text-right text-sm font-bold text-primary">
                {bom.total_weight_kg.toFixed(3)} kg
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}
