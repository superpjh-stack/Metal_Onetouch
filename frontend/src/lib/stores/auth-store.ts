import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { authApi } from '@/lib/api/auth'
import { STORAGE_KEYS } from '@/lib/constants'
import type { User, LoginInput } from '@/types'

// ============================================================
// Auth 스토어 타입
// ============================================================

interface AuthStore {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  // Actions
  login: (credentials: LoginInput) => Promise<void>
  logout: () => Promise<void>
  setTokens: (access: string, refresh: string) => void
  setUser: (user: User) => void
  clearError: () => void
  initializeAuth: () => Promise<void>
}

// ============================================================
// Zustand Auth 스토어
// ============================================================

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      /**
       * 로그인
       */
      login: async (credentials: LoginInput) => {
        set({ isLoading: true, error: null })
        try {
          const response = await authApi.login(credentials)
          const { user, accessToken, refreshToken } = response.data.data

          // 토큰을 로컬 스토리지에도 저장 (axios 인터셉터가 사용)
          if (typeof window !== 'undefined') {
            localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken)
            localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken)
          }

          set({
            user,
            accessToken,
            refreshToken,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })
        } catch (error: unknown) {
          const message =
            (error as { response?: { data?: { error?: { message?: string } } } })
              ?.response?.data?.error?.message ?? '로그인에 실패했습니다.'
          set({ isLoading: false, error: message, isAuthenticated: false })
          throw error
        }
      },

      /**
       * 로그아웃
       */
      logout: async () => {
        try {
          await authApi.logout()
        } catch {
          // 서버 오류 무시, 클라이언트 상태만 클리어
        } finally {
          if (typeof window !== 'undefined') {
            localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN)
            localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN)
            localStorage.removeItem(STORAGE_KEYS.USER)
          }
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            error: null,
          })
        }
      },

      /**
       * 토큰 설정 (토큰 갱신 후 호출)
       */
      setTokens: (access: string, refresh: string) => {
        if (typeof window !== 'undefined') {
          localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, access)
          localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refresh)
        }
        set({ accessToken: access, refreshToken: refresh })
      },

      /**
       * 사용자 정보 업데이트
       */
      setUser: (user: User) => {
        set({ user })
      },

      /**
       * 에러 클리어
       */
      clearError: () => set({ error: null }),

      /**
       * 앱 초기화 시 서버에서 현재 사용자 정보 재확인
       */
      initializeAuth: async () => {
        const { accessToken } = get()
        if (!accessToken) return

        try {
          const response = await authApi.getMe()
          set({ user: response.data.data, isAuthenticated: true })
        } catch {
          // 토큰이 만료된 경우 로그아웃
          if (typeof window !== 'undefined') {
            localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN)
            localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN)
          }
          set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
        }
      },
    }),
    {
      name: 'onetouch-auth',
      storage: createJSONStorage(() =>
        typeof window !== 'undefined' ? localStorage : sessionStorage
      ),
      // 민감 데이터 부분 제외하고 직렬화
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
