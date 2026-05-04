import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { STORAGE_KEYS } from '@/lib/constants'

// ============================================================
// UI 상태 스토어 타입
// ============================================================

interface UiStore {
  // 사이드바
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void

  // 현재 페이지
  pageTitle: string
  setPageTitle: (title: string) => void

  // 전역 로딩
  globalLoading: boolean
  setGlobalLoading: (loading: boolean) => void

  // 알림 패널
  notificationPanelOpen: boolean
  toggleNotificationPanel: () => void

  // 모바일 사이드바
  mobileSidebarOpen: boolean
  setMobileSidebarOpen: (open: boolean) => void
}

// ============================================================
// Zustand UI 스토어
// ============================================================

export const useUiStore = create<UiStore>()(
  persist(
    (set) => ({
      // 사이드바
      sidebarCollapsed: false,
      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed: boolean) =>
        set({ sidebarCollapsed: collapsed }),

      // 현재 페이지 제목
      pageTitle: '원터치 AI+MES',
      setPageTitle: (title: string) => set({ pageTitle: title }),

      // 전역 로딩
      globalLoading: false,
      setGlobalLoading: (loading: boolean) => set({ globalLoading: loading }),

      // 알림 패널
      notificationPanelOpen: false,
      toggleNotificationPanel: () =>
        set((state) => ({
          notificationPanelOpen: !state.notificationPanelOpen,
        })),

      // 모바일 사이드바
      mobileSidebarOpen: false,
      setMobileSidebarOpen: (open: boolean) =>
        set({ mobileSidebarOpen: open }),
    }),
    {
      name: STORAGE_KEYS.SIDEBAR_COLLAPSED,
      storage: createJSONStorage(() =>
        typeof window !== 'undefined' ? localStorage : sessionStorage
      ),
      // 사이드바 상태만 영속화
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    }
  )
)
