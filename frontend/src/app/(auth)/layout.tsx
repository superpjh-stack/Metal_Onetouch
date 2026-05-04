import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: '로그인',
}

// ============================================================
// 인증 레이아웃
// 화면 중앙 정렬, 그라디언트 배경
// ============================================================

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-100 via-blue-50 to-slate-100 dark:from-slate-900 dark:via-blue-950/30 dark:to-slate-900">
      {/* 배경 패턴 (제조업 느낌의 그리드) */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(0,0,0,0.5) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,0,0,0.5) 1px, transparent 1px)
          `,
          backgroundSize: '32px 32px',
        }}
      />

      {/* 중앙 정렬 컨테이너 */}
      <div className="relative flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-[420px]">{children}</div>
      </div>
    </div>
  )
}
