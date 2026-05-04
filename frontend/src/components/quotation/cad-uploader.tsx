'use client'

import { useCallback, useRef, useState } from 'react'
import { useCreateDrawing } from '@/lib/hooks/use-cad'
import { useUploadFile } from '@/lib/hooks/use-files'
import { Button } from '@/components/ui/button'

interface CadUploaderProps {
  customerId?: string
  onDrawingCreated?: (drawingId: string) => void
}

export function CadUploader({ customerId, onDrawingCreated }: CadUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { upload, isPending: uploading } = useUploadFile()
  const createDrawing = useCreateDrawing()

  const isPending = uploading || createDrawing.isPending

  const handleFile = useCallback(
    async (file: File) => {
      setError(null)
      const allowed = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
      if (!allowed.includes(file.type)) {
        setError('JPG / PNG / WebP / PDF 파일만 업로드 가능합니다.')
        return
      }
      if (file.size > 20 * 1024 * 1024) {
        setError('파일 크기는 20MB 이하여야 합니다.')
        return
      }
      try {
        const uploaded = await upload(file, 'cad-drawings')
        const drawing = await createDrawing.mutateAsync({
          file_id: uploaded.id,
          customer_id: customerId,
        })
        onDrawingCreated?.(drawing.id)
      } catch (e) {
        setError('업로드 중 오류가 발생했습니다.')
      }
    },
    [upload, createDrawing, customerId, onDrawingCreated]
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile]
  )

  return (
    <div className="space-y-2">
      <div
        className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/20'
            : 'border-gray-300 dark:border-gray-700'
        } ${isPending ? 'pointer-events-none opacity-60' : 'cursor-pointer hover:border-gray-400'}`}
        onClick={() => !isPending && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".jpg,.jpeg,.png,.webp,.pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) handleFile(file)
            e.target.value = ''
          }}
        />

        {isPending ? (
          <div className="flex flex-col items-center gap-2 text-sm text-gray-500">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
            <span>분석 대기열에 등록 중…</span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-center">
            <svg className="h-10 w-10 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              CAD 도면 파일 드래그 또는 클릭하여 업로드
            </p>
            <p className="text-xs text-gray-500">JPG · PNG · WebP · PDF (최대 20MB)</p>
          </div>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-500">{error}</p>
      )}
    </div>
  )
}
