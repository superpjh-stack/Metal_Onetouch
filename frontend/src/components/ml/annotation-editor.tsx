'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useSubmitAnnotation } from '@/lib/hooks/use-annotation'

interface CadObject {
  type: string
  count?: number
  diameter?: number
  angle?: number
  length?: number
  radius?: number
  layer?: string
}

interface ParsedObjects {
  objects: CadObject[]
  dimensions?: { length: number; width: number; thickness: number }
}

interface AnnotationEditorProps {
  drawingId: string
  originalParsed: ParsedObjects
  onSubmit?: () => void
}

const OBJECT_TYPES = ['hole', 'bend', 'cut', 'weld', 'slot']

export function AnnotationEditor({ drawingId, originalParsed, onSubmit }: AnnotationEditorProps) {
  const [objects, setObjects] = useState<CadObject[]>(
    JSON.parse(JSON.stringify(originalParsed.objects ?? []))
  )
  const [dims, setDims] = useState(
    originalParsed.dimensions ?? { length: 0, width: 0, thickness: 0 }
  )

  const submitAnnotation = useSubmitAnnotation(drawingId)

  const updateObj = (idx: number, field: keyof CadObject, value: string | number) => {
    setObjects((prev) => {
      const next = [...prev]
      next[idx] = { ...next[idx], [field]: value }
      return next
    })
  }

  const removeObj = (idx: number) => {
    setObjects((prev) => prev.filter((_, i) => i !== idx))
  }

  const addObj = () => {
    setObjects((prev) => [...prev, { type: 'hole', count: 1 }])
  }

  const handleSubmit = () => {
    const corrected_parsed = { objects, dimensions: dims }
    submitAnnotation.mutate(corrected_parsed as Record<string, unknown>, {
      onSuccess: () => onSubmit?.(),
    })
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        {(['length', 'width', 'thickness'] as const).map((key) => (
          <div key={key}>
            <Label className="text-xs">{key} (mm)</Label>
            <Input
              type="number"
              value={dims[key]}
              onChange={(e) => setDims((d) => ({ ...d, [key]: parseFloat(e.target.value) || 0 }))}
              className="h-8 text-sm"
            />
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-sm font-medium">객체 목록 ({objects.length}개)</Label>
          <Button variant="outline" size="sm" onClick={addObj}>
            + 추가
          </Button>
        </div>

        {objects.map((obj, idx) => (
          <div key={idx} className="flex items-center gap-2 rounded border p-2">
            <Select value={obj.type} onValueChange={(v) => updateObj(idx, 'type', v)}>
              <SelectTrigger className="h-8 w-24 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {OBJECT_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Input
              type="number"
              placeholder="개수"
              value={obj.count ?? 1}
              onChange={(e) => updateObj(idx, 'count', parseInt(e.target.value) || 1)}
              className="h-8 w-16 text-xs"
            />

            {obj.type === 'hole' && (
              <Input
                type="number"
                placeholder="직경mm"
                value={obj.diameter ?? ''}
                onChange={(e) => updateObj(idx, 'diameter', parseFloat(e.target.value))}
                className="h-8 w-20 text-xs"
              />
            )}
            {obj.type === 'bend' && (
              <Input
                type="number"
                placeholder="각도°"
                value={obj.angle ?? ''}
                onChange={(e) => updateObj(idx, 'angle', parseFloat(e.target.value))}
                className="h-8 w-20 text-xs"
              />
            )}
            {['cut', 'weld', 'slot'].includes(obj.type) && (
              <Input
                type="number"
                placeholder="길이mm"
                value={obj.length ?? ''}
                onChange={(e) => updateObj(idx, 'length', parseFloat(e.target.value))}
                className="h-8 w-20 text-xs"
              />
            )}

            <Button
              variant="ghost"
              size="sm"
              className="ml-auto h-7 w-7 p-0 text-destructive"
              onClick={() => removeObj(idx)}
            >
              ×
            </Button>
          </div>
        ))}
      </div>

      <div className="flex justify-end gap-2">
        <Button
          onClick={handleSubmit}
          disabled={submitAnnotation.isPending}
          size="sm"
        >
          {submitAnnotation.isPending ? '저장 중...' : '보정 완료'}
        </Button>
      </div>
    </div>
  )
}
