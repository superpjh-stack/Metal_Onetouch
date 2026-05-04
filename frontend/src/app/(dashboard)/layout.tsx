'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Sidebar } from '@/components/layout/sidebar'
import { Header } from '@/components/layout/header'
import { useAuthStore } from '@/lib/stores/auth-store'
import { useUiStore } from '@/lib/stores/ui-store'
import { ROUTES } from '@/lib/constants'
import { cn } from '@/lib/utils/format'

// ============================================================
// 대시보드 레이아웃
// 인증 체크 + Sidebar + Header + main content
// ============================================================

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const { isAuthenticated, initializeAuth } = useAuthStore()
  const { mobileSidebarOpen, setMobileSidebarOpen, sidebarCollapsed } = useUiStore()

  // 인증 체크: 미로그인 시 /login 리다이렉트
  useEffect(() => {
    if (!isAuthenticated) {
      router.replace(ROUTES.LOGIN)
      return
    }
    // 서버에서 현재 사용자 정보 재확인
    initializeAuth()
  }, [isAuthenticated, router, initializeAuth])

  // 미인증 상태에서는 아무것도 렌더링하지 않음
  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* 사이드바 (데스크탑) */}
      <div className="hidden lg:flex lg:shrink-0">
        <Sidebar />
      </div>

      {/* 모바일 사이드바 오버레이 */}
      {mobileSidebarOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            onClick={() => setMobileSidebarOpen(false)}
          />
          <div className="fixed inset-y-0 left-0 z-50 flex lg:hidden">
            <Sidebar />
          </div>
        </>
      )}

      {/* 메인 영역 */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* 헤더 */}
        <Header />

        {/* 콘텐츠 */}
        <main
          className={cn(
            'flex-1 overflow-y-auto p-4 lg:p-6',
            'transition-all duration-300'
          )}
        >
          {children}
        </main>
      </div>
    </div>
  )
}
