import { useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'

export interface PresignedUploadResponse {
  file_id: string
  presigned_url: string
  object_key: string
  expires_in: number
}

export interface UploadedFileRead {
  id: string
  bucket: string
  object_key: string
  original_name: string
  mime_type: string | null
  file_size: number | null
  file_hash: string | null
  created_at: string
}

export interface DownloadUrlResponse {
  download_url: string
  expires_in: number
}

async function sha256Hex(buffer: ArrayBuffer): Promise<string> {
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer)
  return Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

export function usePresignedUpload() {
  return useMutation({
    mutationFn: (req: { original_name: string; mime_type: string; folder: string }) =>
      apiClient
        .post<PresignedUploadResponse>('/api/v1/files/presigned-upload', req)
        .then((r) => r.data),
  })
}

export function useConfirmUpload() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: { file_id: string; file_size: number; file_hash: string }) =>
      apiClient
        .post<UploadedFileRead>('/api/v1/files/confirm-upload', req)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['files'] })
    },
  })
}

/** Convenience: presigned upload → PUT to MinIO → confirm, returns file_id */
export function useUploadFile() {
  const presign = usePresignedUpload()
  const confirm = useConfirmUpload()

  const upload = async (file: File, folder = 'cad-drawings'): Promise<UploadedFileRead> => {
    const { file_id, presigned_url } = await presign.mutateAsync({
      original_name: file.name,
      mime_type: file.type || 'application/octet-stream',
      folder,
    })

    const buffer = await file.arrayBuffer()
    await fetch(presigned_url, {
      method: 'PUT',
      headers: { 'Content-Type': file.type || 'application/octet-stream' },
      body: buffer,
    })

    const file_hash = await sha256Hex(buffer)
    return confirm.mutateAsync({ file_id, file_size: file.size, file_hash })
  }

  return {
    upload,
    isPending: presign.isPending || confirm.isPending,
    error: presign.error ?? confirm.error,
  }
}
