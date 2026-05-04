'use client'

import { useState } from 'react'
import type { QuotationItemRead } from '@/lib/hooks/use-quotations'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const TYPE_LABEL: Record<string, string> = {
  material: '소재비',
  cutting:  '절단',
  drilling: '드릴링',
  bending:  '벤딩',
  welding:  '용접',
}

interface Props {
  items: QuotationItemRead[]
  editable?: boolean
  onSave?: (updates: { id: string; unit_price: string; quantity?: string }[]) => void
  saving?: boolean
}

export function QuotationItemsTable({ items, editable, onSave, saving }: Props) {
  const [edits, setEdits] = useState<Record<string, { unit_price: string; quantity: string }>>(() =>
    Object.fromEntries(items.map((i) => [i.id, { unit_price: i.unit_price, quantity: i.quantity }]))
  )

  const total = items.reduce((sum, item) => {
    const edit = edits[item.id]
    if (edit) {
      const qty = parseFloat(edit.quantity || item.quantity)
      const up = parseFloat(edit.unit_price || item.unit_price)
      return sum + qty * up
    }
    return sum + parseFloat(item.amount)
  }, 0)

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="border-b bg-gray-50 dark:bg-gray-800">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-300">항목</th>
              <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-300">설명</th>
              <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-300">수량</th>
              <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-300">단가</th>
              <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-300">금액</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {items.map((item) => {
              const edit = edits[item.id]
              const qty = parseFloat(edit?.quantity ?? item.quantity)
              const up = parseFloat(edit?.unit_price ?? item.unit_price)
              const amt = qty * up

              return (
                <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="px-3 py-2">
                    <span className="rounded bg-blue-50 px-1.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-950/30 dark:text-blue-400">
                      {TYPE_LABEL[item.item_type] ?? item.item_type}
                    </span>
                  </td>
                  <td className="max-w-[200px] truncate px-3 py-2 text-gray-600 dark:text-gray-400">
                    {item.description ?? '-'}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {editable ? (
                      <Input
                        type="number"
                        className="w-20 text-right text-sm"
                        value={edit?.quantity ?? item.quantity}
                        onChange={(e) =>
                          setEdits((prev) => ({
                            ...prev,
                            [item.id]: { ...prev[item.id], quantity: e.target.value },
                          }))
                        }
                      />
                    ) : (
                      <span>
                        {parseFloat(item.quantity).toLocaleString()} {item.unit ?? ''}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {editable ? (
                      <Input
                        type="number"
                        className="w-28 text-right text-sm"
                        value={edit?.unit_price ?? item.unit_price}
                        onChange={(e) =>
                          setEdits((prev) => ({
                            ...prev,
                            [item.id]: { ...prev[item.id], unit_price: e.target.value },
                          }))
                        }
                      />
                    ) : (
                      <span>₩{parseFloat(item.unit_price).toLocaleString()}</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right font-medium">
                    ₩{amt.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}
                  </td>
                </tr>
              )
            })}
          </tbody>
          <tfoot className="border-t bg-gray-50 dark:bg-gray-800">
            <tr>
              <td colSpan={4} className="px-3 py-2 text-right font-semibold">합계</td>
              <td className="px-3 py-2 text-right font-bold text-blue-700 dark:text-blue-400">
                ₩{total.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      {editable && onSave && (
        <div className="flex justify-end">
          <Button
            size="sm"
            disabled={saving}
            onClick={() =>
              onSave(
                items.map((item) => ({
                  id: item.id,
                  unit_price: edits[item.id]?.unit_price ?? item.unit_price,
                  quantity: edits[item.id]?.quantity,
                }))
              )
            }
          >
            {saving ? '저장 중…' : '단가 저장'}
          </Button>
        </div>
      )}
    </div>
  )
}
