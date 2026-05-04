'use client'

import { useEffect } from 'react'
import { Truck } from 'lucide-react'
import { useUiStore } from '@/lib/stores/ui-store'

export default function ShipmentPage() {
  const { setPageTitle } = useUiStore()
  useEffect(() => { setPageTitle('출하물류') }, [setPageTitle])

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 py-20 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
        <Truck className="h-8 w-8 text-muted-foreground" />
      </div>
      <div>
        <h2 className="text-xl font-semibold text-foreground">출하물류</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          출하 처리, 배송 현황, 클레임 관리
        </p>
        <p className="mt-2 text-xs text-muted-foreground">개발 예정</p>
      </div>
    </div>
  )
}
