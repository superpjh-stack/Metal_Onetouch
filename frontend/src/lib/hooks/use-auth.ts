'use client'

import { useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth-store'
import { ROUTES, ROLES, type RoleValue } from '@/lib/constants'
import type { LoginInput } from '@/types'

// ============================================================
// useAuth 훅
// 로그인 상태 및 역할 기반 접근 제어
// ============================================================

export function useAuth() {
  const router = useRouter()
  const {
    user,
    accessToken,
    isAuthenticated,
    isLoading,
    error,
    login: storeLogin,
    logout: storeLogout,
    clearError,
  } = useAuthStore()

  /**
   * 로그인 (성공 시 대시보드로 이동)
   */
  const login = useCallback(
    async (credentials: LoginInput) => {
      await storeLogin(credentials)
      router.push(ROUTES.DASHBOARD)
    },
    [storeLogin, router]
  )

  /**
   * 로그아웃 (로그인 페이지로 이동)
   */
  const logout = useCallback(async () => {
    await storeLogout()
    router.push(ROUTES.LOGIN)
  }, [storeLogout, router])

  /**
   * 특정 역할 보유 여부 확인
   */
  const hasRole = useCallback(
    (role: RoleValue): boolean => {
      return user?.role === role
    },
    [user]
  )

  /**
   * 여러 역할 중 하나 이상 보유 여부 확인
   */
  const hasAnyRole = useCallback(
    (roles: RoleValue[]): boolean => {
      if (!user) return false
      return roles.includes(user.role as RoleValue)
    },
    [user]
  )

  /**
   * 관리자 여부
   */
  const isAdmin = user?.role === 'admin'

  /**
   * 생산 관리자 여부
   */
  const isProductionManager = user?.role === ROLES.PRODUCTION_MANAGER

  /**
   * 경영진 여부
   */
  const isExecutive = user?.role === ROLES.EXECUTIVE

  /**
   * 품질 검사원 여부
   */
  const isQualityInspector = user?.role === ROLES.QUALITY_INSPECTOR

  /**
   * 영업 엔지니어 여부
   */
  const isSalesEngineer = user?.role === ROLES.SALES_ENGINEER

  return {
    user,
    accessToken,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    clearError,
    hasRole,
    hasAnyRole,
    isAdmin,
    isProductionManager,
    isExecutive,
    isQualityInspector,
    isSalesEngineer,
  }
}
