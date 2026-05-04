'use client'

import type { QuotationRead } from '@/lib/hooks/use-quotations'
import { StatusBadge } from '@/components/ui/status-badge'
import { QuotationItemsTable } from './quotation-items-table'
import { useUpdateQuotationItems, useSubmitQuotation } from '@/lib/hooks/use-quotations'
import { Button } from '@/components/ui/button'

const STATUS_LABEL: Record<string, string> = {
  draft:     '초안',
  submitted: '제출됨',
  accepted:  '수락됨',
  rejected:  '거절됨',
  expired:   '만료됨',
}

interface QuotationPreviewProps {
  quotation: QuotationRead
}

export function QuotationPreview({ quotation }: QuotationPreviewProps) {
  const updateItems = useUpdateQuotationItems()
  const submit = useSubmitQuotation()

  const isDraft = quotation.status === 'draft'
  const marginPct = (parseFloat(quotation.margin_rate) * 100).toFixed(1)

  return (
    <div className="space-y-4 rounded-lg border bg-white p-6 dark:bg-gray-900">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-mono text-lg font-bold">{quotation.quotation_number}</h2>
          {quotation.customer_name && (
            <p className="text-sm text-gray-600 dark:text-gray-400">{quotation.customer_name}</p>
          )}
        </div>
        <StatusBadge status={quotation.status} label={STATUS_LABEL[quotation.status]} />
      </div>

      {/* Cost breakdown */}
      <div className="grid grid-cols-3 gap-3 rounded-lg bg-gray-50 p-3 text-sm dark:bg-gray-800">
        <div>
          <p className="text-gray-500">소재비</p>
          <p className="font-semibold">
            ₩{parseFloat(quotation.material_cost).toLocaleString('ko-KR', { maximumFractionDigits: 0 })}
          </p>
        </div>
        <div>
          <p className="text-gray-500">공정비</p>
          <p className="font-semibold">
            ₩{parseFloat(quotation.process_cost).toLocaleString('ko-KR', { maximumFractionDigits: 0 })}
          </p>
        </div>
        <div>
          <p className="text-gray-500">마진 ({marginPct}%)</p>
          <p className="font-semibold">
            ₩{(parseFloat(quotation.final_amount) - parseFloat(quotation.total_amount)).toLocaleString('ko-KR', { maximumFractionDigits: 0 })}
          </p>
        </div>
      </div>

      {/* Final amount */}
      <div className="flex items-center justify-between rounded-lg bg-blue-50 px-4 py-3 dark:bg-blue-950/30">
        <span className="font-semibold text-blue-900 dark:text-blue-100">최종 견적 금액</span>
        <span className="text-xl font-bold text-blue-700 dark:text-blue-400">
          ₩{parseFloat(quotation.final_amount).toLocaleString('ko-KR', { maximumFractionDigits: 0 })}
        </span>
      </div>

      {/* Items */}
      <QuotationItemsTable
        items={quotation.items}
        editable={isDraft}
        saving={updateItems.isPending}
        onSave={(updates) =>
          updateItems.mutateAsync({ id: quotation.id, items: updates })
        }
      />

      {/* Actions */}
      {isDraft && (
        <div className="flex justify-end gap-2">
          <Button
            variant="default"
            disabled={submit.isPending}
            onClick={() => submit.mutateAsync(quotation.id)}
          >
            {submit.isPending ? '제출 중…' : '견적 제출'}
          </Button>
        </div>
      )}

      {quotation.valid_until && (
        <p className="text-right text-xs text-gray-500">
          유효기간: {quotation.valid_until}
        </p>
      )}
    </div>
  )
}
