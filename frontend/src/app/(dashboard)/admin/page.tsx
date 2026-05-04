'use client'

import { useEffect } from 'react'
import { Users } from 'lucide-react'
import { useUiStore } from '@/lib/stores/ui-store'
import { useAuth } from '@/lib/hooks/use-auth'

export default function AdminPage() {
  const { setPageTitle } = useUiStore()
  const { isAdmin } = useAuth()

  useEffect(() => { setPageTitle('시스템관리') }, [setPageTitle])

  if (!isAdmin) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 py-20 text-center">
        <p className="text-sm text-muted-foreground">
          시스템 관리자 권한이 필요합니다.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 py-20 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
        <Users className="h-8 w-8 text-muted-foreground" />
      </div>
      <div>
        <h2 className="text-xl font-semibold text-foreground">시스템관리</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          사용자 관리, RBAC 역할 설정, 시스템 로그 감사
        </p>
        <p className="mt-2 text-xs text-muted-foreground">개발 예정</p>
      </div>
    </div>
  )
}
