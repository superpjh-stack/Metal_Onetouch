'use client'

import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Cpu, Loader2, Eye, EyeOff } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '@/lib/hooks/use-auth'
import { useRouter } from 'next/navigation'
import { ROUTES } from '@/lib/constants'

// ============================================================
// 로그인 폼 스키마 (Zod 검증)
// ============================================================

const loginSchema = z.object({
  email: z
    .string()
    .min(1, '이메일을 입력해주세요.')
    .email('올바른 이메일 형식이 아닙니다.'),
  password: z
    .string()
    .min(1, '비밀번호를 입력해주세요.')
    .min(6, '비밀번호는 최소 6자 이상이어야 합니다.'),
})

type LoginFormValues = z.infer<typeof loginSchema>

// ============================================================
// 로그인 페이지
// ============================================================

export default function LoginPage() {
  const router = useRouter()
  const { login, isLoading, error, isAuthenticated, clearError } = useAuth()
  const [showPassword, setShowPassword] = useState(false)

  // 이미 로그인된 경우 대시보드로 리다이렉트
  useEffect(() => {
    if (isAuthenticated) {
      router.replace(ROUTES.DASHBOARD)
    }
  }, [isAuthenticated, router])

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  })

  const quickLogin = async () => {
    clearError()
    try {
      await login({ email: 'admin@onetouch.com', password: 'Admin1234!' })
    } catch {
      // 에러는 useAuth store에서 관리
    }
  }

  const onSubmit = async (data: LoginFormValues) => {
    clearError()
    try {
      await login(data)
    } catch {
      // 에러는 useAuth store에서 관리
    }
  }

  return (
    <div className="rounded-2xl border bg-card p-8 shadow-xl">
      {/* 로고 */}
      <div className="mb-8 text-center">
        <div className="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-primary shadow-lg">
          <Cpu className="h-8 w-8 text-primary-foreground" />
        </div>
        <h1 className="text-2xl font-bold text-foreground">원터치 AI+MES</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          금속 가공 제조 통합 관리 시스템
        </p>
      </div>

      {/* 로그인 폼 */}
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        {/* 이메일 */}
        <div className="space-y-1.5">
          <label
            htmlFor="email"
            className="text-sm font-medium text-foreground"
          >
            이메일
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="user@onetouch.co.kr"
            {...register('email')}
            className={[
              'w-full rounded-lg border bg-background px-3 py-2.5 text-sm',
              'placeholder:text-muted-foreground',
              'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
              'disabled:cursor-not-allowed disabled:opacity-50',
              'transition-colors',
              errors.email
                ? 'border-destructive focus:ring-destructive'
                : 'border-input',
            ].join(' ')}
            disabled={isLoading}
          />
          {errors.email && (
            <p className="text-xs text-destructive">{errors.email.message}</p>
          )}
        </div>

        {/* 비밀번호 */}
        <div className="space-y-1.5">
          <label
            htmlFor="password"
            className="text-sm font-medium text-foreground"
          >
            비밀번호
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              placeholder="••••••••"
              {...register('password')}
              className={[
                'w-full rounded-lg border bg-background px-3 py-2.5 pr-10 text-sm',
                'placeholder:text-muted-foreground',
                'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
                'disabled:cursor-not-allowed disabled:opacity-50',
                'transition-colors',
                errors.password
                  ? 'border-destructive focus:ring-destructive'
                  : 'border-input',
              ].join(' ')}
              disabled={isLoading}
            />
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              tabIndex={-1}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
          {errors.password && (
            <p className="text-xs text-destructive">{errors.password.message}</p>
          )}
        </div>

        {/* API 에러 메시지 */}
        {error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* 로그인 버튼 */}
        <button
          type="submit"
          disabled={isLoading}
          className={[
            'w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground',
            'hover:bg-primary/90 active:bg-primary/80',
            'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'transition-all duration-150',
            'flex items-center justify-center gap-2',
          ].join(' ')}
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              로그인 중...
            </>
          ) : (
            '로그인'
          )}
        </button>
      </form>

      {/* 퀵 로그인 */}
      <div className="mt-4 rounded-lg border border-dashed border-muted-foreground/30 p-3">
        <p className="mb-2 text-center text-xs text-muted-foreground">개발용 빠른 로그인</p>
        <button
          type="button"
          onClick={quickLogin}
          disabled={isLoading}
          className="w-full rounded-md border border-muted-foreground/20 bg-muted px-3 py-2 text-xs text-muted-foreground hover:bg-muted/80 disabled:opacity-50 transition-colors"
        >
          admin@onetouch.com
        </button>
      </div>

      {/* 하단 안내 */}
      <p className="mt-4 text-center text-xs text-muted-foreground">
        계정 문의:{' '}
        <span className="font-medium text-foreground">시스템 관리자</span>에게
        연락하세요.
      </p>
    </div>
  )
}
