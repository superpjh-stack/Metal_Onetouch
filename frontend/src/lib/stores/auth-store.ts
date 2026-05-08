import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import axios from 'axios'
import { authApi } from '@/lib/api/auth'
import { STORAGE_KEYS } from '@/lib/constants'
import type { User, LoginInput } from '@/types'

// 백엔드 /me 응답 → User 타입 변환
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapMeToUser(d: any): User {
  return {
    id: d.id,
    email: d.email,
    name: d.full_name ?? d.name ?? '',
    role: d.role,
    department: d.department,
    isActive: d.is_active ?? d.isActive ?? true,
    createdAt: d.created_at ?? d.createdAt ?? '',
    updatedAt: d.updated_at ?? d.updatedAt ?? '',
  }
}

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
          // 백엔드: { access_token, refresh_token, token_type, expires_in }
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const data = response.data as any
          const accessToken: string = data.access_token ?? data.accessToken
          const refreshToken: string = data.refresh_token ?? data.refreshToken

          if (typeof window !== 'undefined') {
            localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken)
            localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken)
          }

          // 토큰을 axios 기본 헤더에 주입 후 /me 호출
          axios.defaults.headers.common.Authorization = `Bearer ${accessToken}`
          const meRes = await authApi.getMe()
          const user = mapMeToUser(meRes.data)

          set({
            user,
            accessToken,
            refreshToken,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })
        } catch (error: unknown) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const errData = (error as any)?.response?.data
          const message =
            errData?.detail ?? errData?.error?.message ?? '로그인에 실패했습니다.'
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
          const user = mapMeToUser(response.data)
          set({ user, isAuthenticated: true })
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
