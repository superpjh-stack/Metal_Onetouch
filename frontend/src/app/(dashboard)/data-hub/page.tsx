'use client'

import { useEffect } from 'react'
import { Database } from 'lucide-react'
import { useUiStore } from '@/lib/stores/ui-store'

export default function DataHubPage() {
  const { setPageTitle } = useUiStore()
  useEffect(() => { setPageTitle('데이터허브') }, [setPageTitle])

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 py-20 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
        <Database className="h-8 w-8 text-muted-foreground" />
      </div>
      <div>
        <h2 className="text-xl font-semibold text-foreground">데이터허브</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          IoT 센서 데이터, 시계열 분석, TimescaleDB 연동
        </p>
        <p className="mt-2 text-xs text-muted-foreground">개발 예정</p>
      </div>
    </div>
  )
}
