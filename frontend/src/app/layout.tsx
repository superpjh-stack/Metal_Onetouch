import type { Metadata } from 'next'
import { Toaster } from 'sonner'
import { Providers } from './providers'
import './globals.css'

// ============================================================
// 루트 메타데이터
// ============================================================

export const metadata: Metadata = {
  title: {
    default: '원터치 AI+MES',
    template: '%s | 원터치 AI+MES',
  },
  description: '금속 가공 제조업 AI 통합 MES 시스템 — LOT 추적, 공정관리, 품질관리, AI Agent',
  keywords: ['MES', 'AI', '제조', '금속가공', '공정관리', 'LOT추적'],
  authors: [{ name: '원터치 (Onetouch)' }],
  robots: {
    index: false,
    follow: false,
  },
}

// ============================================================
// 루트 레이아웃
// ============================================================

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <head>
        {/* Pretendard 폰트 (CDN) */}
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
        />
      </head>
      <body>
        <Providers>
          {children}
        </Providers>
        {/* Sonner 토스트 알림 */}
        <Toaster
          position="top-right"
          richColors
          closeButton
          duration={4000}
          toastOptions={{
            style: {
              fontFamily: 'var(--font-sans)',
            },
          }}
        />
      </body>
    </html>
  )
}
