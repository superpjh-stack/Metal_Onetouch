import apiClient from './client'
import type { LoginInput, LoginResponse, User, ApiResponse } from '@/types'

// ============================================================
// 인증 API 함수들
// ============================================================

export const authApi = {
  /**
   * 로그인
   * POST /api/v1/auth/login
   */
  login: (credentials: LoginInput) =>
    apiClient.post<ApiResponse<LoginResponse>>('/api/v1/auth/login', credentials),

  /**
   * 로그아웃
   * POST /api/v1/auth/logout
   */
  logout: () =>
    apiClient.post<ApiResponse<void>>('/api/v1/auth/logout'),

  /**
   * 토큰 갱신
   * POST /api/v1/auth/refresh
   */
  refresh: (refreshToken: string) =>
    apiClient.post<ApiResponse<{ accessToken: string; expiresIn: number }>>(
      '/api/v1/auth/refresh',
      { refreshToken }
    ),

  /**
   * 현재 사용자 정보 조회
   * GET /api/v1/auth/me
   */
  getMe: () =>
    apiClient.get<ApiResponse<User>>('/api/v1/auth/me'),

  /**
   * 비밀번호 변경
   * PATCH /api/v1/auth/password
   */
  changePassword: (data: { currentPassword: string; newPassword: string }) =>
    apiClient.patch<ApiResponse<void>>('/api/v1/auth/password', data),
}
