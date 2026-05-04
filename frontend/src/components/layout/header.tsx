'use client'

import { Bell, LogOut, User, Settings, ChevronDown, Menu } from 'lucide-react'
import { useUiStore } from '@/lib/stores/ui-store'
import { useAuth } from '@/lib/hooks/use-auth'
import { ROLE_LABELS } from '@/lib/constants'
import type { RoleValue } from '@/lib/constants'

// ============================================================
// Header 컴포넌트
// ============================================================

export function Header() {
  const { pageTitle, toggleNotificationPanel, setMobileSidebarOpen } = useUiStore()
  const { user, logout } = useAuth()

  return (
    <header className="flex h-16 items-center justify-between border-b bg-card px-4 lg:px-6">
      {/* 좌측: 모바일 메뉴 버튼 + 페이지 제목 */}
      <div className="flex items-center gap-3">
        {/* 모바일 햄버거 메뉴 */}
        <button
          onClick={() => setMobileSidebarOpen(true)}
          className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-accent lg:hidden"
          aria-label="메뉴 열기"
        >
          <Menu className="h-5 w-5 text-muted-foreground" />
        </button>

        {/* 페이지 제목 / 브레드크럼 */}
        <div>
          <h1 className="text-lg font-semibold text-foreground">{pageTitle}</h1>
        </div>
      </div>

      {/* 우측: 알림 + 사용자 */}
      <div className="flex items-center gap-2">
        {/* 알림 벨 */}
        <button
          onClick={toggleNotificationPanel}
          className="relative flex h-9 w-9 items-center justify-center rounded-lg hover:bg-accent"
          aria-label="알림"
        >
          <Bell className="h-5 w-5 text-muted-foreground" />
          {/* 알림 뱃지 (더미) */}
          <span className="absolute right-1.5 top-1.5 flex h-2 w-2 items-center justify-center rounded-full bg-destructive">
            <span className="sr-only">새 알림</span>
          </span>
        </button>

        {/* 사용자 드롭다운 */}
        <UserDropdown user={user} onLogout={logout} />
      </div>
    </header>
  )
}

// ============================================================
// 사용자 드롭다운 (간이 구현 - Radix DropdownMenu 없이)
// ============================================================

interface UserDropdownProps {
  user: { name: string; email: string; role: string } | null
  onLogout: () => void
}

function UserDropdown({ user, onLogout }: UserDropdownProps) {
  if (!user) return null

  return (
    <div className="group relative">
      {/* 트리거 */}
      <button className="flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-accent">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
          {user.name.charAt(0)}
        </div>
        <div className="hidden text-left lg:block">
          <p className="text-sm font-medium text-foreground leading-tight">
            {user.name}
          </p>
          <p className="text-xs text-muted-foreground">
            {ROLE_LABELS[user.role as RoleValue] ?? user.role}
          </p>
        </div>
        <ChevronDown className="hidden h-4 w-4 text-muted-foreground lg:block" />
      </button>

      {/* 드롭다운 메뉴 */}
      <div
        className={[
          'absolute right-0 top-full z-50 mt-1 w-56',
          'rounded-lg border bg-popover shadow-lg',
          'invisible opacity-0 translate-y-1',
          'transition-all duration-150',
          'group-focus-within:visible group-focus-within:opacity-100 group-focus-within:translate-y-0',
          'group-hover:visible group-hover:opacity-100 group-hover:translate-y-0',
        ].join(' ')}
      >
        {/* 사용자 정보 */}
        <div className="border-b px-4 py-3">
          <p className="text-sm font-medium text-foreground">{user.name}</p>
          <p className="text-xs text-muted-foreground truncate">{user.email}</p>
        </div>

        {/* 메뉴 아이템 */}
        <div className="p-1">
          <button className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-foreground hover:bg-accent">
            <User className="h-4 w-4 text-muted-foreground" />
            내 프로필
          </button>
          <button className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-foreground hover:bg-accent">
            <Settings className="h-4 w-4 text-muted-foreground" />
            설정
          </button>
        </div>

        {/* 로그아웃 */}
        <div className="border-t p-1">
          <button
            onClick={onLogout}
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-destructive hover:bg-destructive/10"
          >
            <LogOut className="h-4 w-4" />
            로그아웃
          </button>
        </div>
      </div>
    </div>
  )
}
