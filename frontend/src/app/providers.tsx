'use client'

import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// ============================================================
// 클라이언트 프로바이더 모음
// TanStack Query는 'use client' 경계가 필요하므로 별도 파일로 분리
// ============================================================

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // 윈도우 포커스 시 자동 재조회
            refetchOnWindowFocus: false,
            // 재시도 횟수
            retry: 1,
            // 데이터 신선도 유지 시간 (5분)
            staleTime: 5 * 60 * 1000,
          },
          mutations: {
            // 뮤테이션 재시도 없음
            retry: 0,
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}
