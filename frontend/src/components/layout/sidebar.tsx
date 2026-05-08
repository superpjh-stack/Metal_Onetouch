'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Factory,
  Package,
  Truck,
  FileText,
  Settings2,
  BarChart2,
  Database,
  Bot,
  Users,
  ChevronLeft,
  ChevronRight,
  Cpu,
  Brain,
  Tag,
  ShoppingCart,
} from 'lucide-react'
import { cn } from '@/lib/utils/format'
import { useUiStore } from '@/lib/stores/ui-store'
import { ROUTES } from '@/lib/constants'
import type { LucideIcon } from 'lucide-react'

// ============================================================
// 내비게이션 메뉴 아이템 정의
// ============================================================

interface NavItem {
  label: string
  href: string
  icon: LucideIcon
  badge?: string
}

const navItems: NavItem[] = [
  { label: 'AI 대시보드', href: ROUTES.DASHBOARD, icon: LayoutDashboard },
  { label: '공정관리', href: ROUTES.PROCESS, icon: Factory },
  { label: '입고재고', href: ROUTES.INVENTORY, icon: Package },
  { label: '출하물류', href: ROUTES.SHIPMENT, icon: Truck },
  { label: '수주관리', href: '/orders', icon: ShoppingCart },
  { label: '수주견적 AI', href: ROUTES.QUOTATION, icon: FileText },
  { label: '기준정보', href: ROUTES.MASTER_DATA, icon: Settings2 },
  { label: 'KPI', href: ROUTES.KPI, icon: BarChart2 },
  { label: '데이터허브', href: ROUTES.DATA_HUB, icon: Database },
  { label: 'AI Agent', href: ROUTES.AI_AGENT, icon: Bot },
  { label: 'ML 학습', href: '/ml/training', icon: Brain },
  { label: '어노테이션', href: '/ml/annotation', icon: Tag },
  { label: '시스템관리', href: ROUTES.SYSTEM, icon: Users },
]

// ============================================================
// Sidebar 컴포넌트
// ============================================================

export function Sidebar() {
  const pathname = usePathname()
  const { sidebarCollapsed, toggleSidebar } = useUiStore()

  return (
    <aside
      className={cn(
        'relative flex h-full flex-col border-r bg-card transition-all duration-300',
        sidebarCollapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* 로고 영역 */}
      <div
        className={cn(
          'flex h-16 items-center border-b px-4',
          sidebarCollapsed ? 'justify-center' : 'justify-between'
        )}
      >
        {!sidebarCollapsed && (
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Cpu className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <p className="text-sm font-bold leading-tight text-foreground">
                원터치
              </p>
              <p className="text-[10px] text-muted-foreground">AI+MES</p>
            </div>
          </div>
        )}

        {sidebarCollapsed && (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Cpu className="h-5 w-5 text-primary-foreground" />
          </div>
        )}
      </div>

      {/* 네비게이션 */}
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-1 px-2">
          {navItems.map((item) => {
            const isActive =
              item.href === ROUTES.DASHBOARD
                ? pathname === item.href
                : pathname.startsWith(item.href)

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    'group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all',
                    'hover:bg-accent hover:text-accent-foreground',
                    isActive
                      ? 'bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground'
                      : 'text-muted-foreground',
                    sidebarCollapsed && 'justify-center px-2'
                  )}
                  title={sidebarCollapsed ? item.label : undefined}
                >
                  <item.icon
                    className={cn(
                      'h-5 w-5 shrink-0',
                      isActive
                        ? 'text-primary-foreground'
                        : 'text-muted-foreground group-hover:text-accent-foreground'
                    )}
                  />
                  {!sidebarCollapsed && (
                    <span className="flex-1 truncate">{item.label}</span>
                  )}
                  {!sidebarCollapsed && item.badge && (
                    <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-destructive px-1.5 text-[10px] font-semibold text-destructive-foreground">
                      {item.badge}
                    </span>
                  )}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* 접힘/펼침 토글 버튼 */}
      <button
        onClick={toggleSidebar}
        className={cn(
          'absolute -right-3 top-20 flex h-6 w-6 items-center justify-center',
          'rounded-full border bg-background shadow-md transition-all',
          'hover:bg-accent hover:shadow-lg'
        )}
        aria-label={sidebarCollapsed ? '사이드바 펼치기' : '사이드바 접기'}
      >
        {sidebarCollapsed ? (
          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
        ) : (
          <ChevronLeft className="h-3.5 w-3.5 text-muted-foreground" />
        )}
      </button>
    </aside>
  )
}
