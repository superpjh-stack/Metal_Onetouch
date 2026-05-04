'use client'

import { useEffect, useRef, useCallback } from 'react'
import { io, Socket } from 'socket.io-client'
import { useAuthStore } from '@/lib/stores/auth-store'

// ============================================================
// useSocket 훅
// Socket.io 연결 및 이벤트 구독 관리
// ============================================================

interface UseSocketOptions {
  /** 자동 연결 여부 (기본: true) */
  autoConnect?: boolean
  /** 재연결 시도 횟수 (기본: 5) */
  reconnectionAttempts?: number
}

interface UseSocketReturn {
  socket: Socket | null
  isConnected: boolean
  /** 이벤트 구독 */
  on: (event: string, handler: (...args: unknown[]) => void) => void
  /** 이벤트 구독 해제 */
  off: (event: string, handler?: (...args: unknown[]) => void) => void
  /** 이벤트 발신 */
  emit: (event: string, ...args: unknown[]) => void
}

export function useSocket(
  namespace = '/',
  options: UseSocketOptions = {}
): UseSocketReturn {
  const { autoConnect = true, reconnectionAttempts = 5 } = options
  const { accessToken } = useAuthStore()

  const socketRef = useRef<Socket | null>(null)
  const isConnectedRef = useRef(false)

  useEffect(() => {
    if (!autoConnect || !accessToken) return

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000'
    const namespaceUrl = namespace === '/' ? wsUrl : `${wsUrl}${namespace}`

    const socket = io(namespaceUrl, {
      auth: {
        token: accessToken,
      },
      reconnection: true,
      reconnectionAttempts,
      reconnectionDelay: 1000,
      transports: ['websocket', 'polling'],
    })

    socket.on('connect', () => {
      isConnectedRef.current = true
    })

    socket.on('disconnect', () => {
      isConnectedRef.current = false
    })

    socket.on('connect_error', (err) => {
      console.error('[Socket] Connection error:', err.message)
    })

    socketRef.current = socket

    return () => {
      socket.disconnect()
      socketRef.current = null
      isConnectedRef.current = false
    }
  }, [autoConnect, accessToken, namespace, reconnectionAttempts])

  const on = useCallback(
    (event: string, handler: (...args: unknown[]) => void) => {
      socketRef.current?.on(event, handler)
    },
    []
  )

  const off = useCallback(
    (event: string, handler?: (...args: unknown[]) => void) => {
      if (handler) {
        socketRef.current?.off(event, handler)
      } else {
        socketRef.current?.off(event)
      }
    },
    []
  )

  const emit = useCallback((event: string, ...args: unknown[]) => {
    socketRef.current?.emit(event, ...args)
  }, [])

  return {
    socket: socketRef.current,
    isConnected: isConnectedRef.current,
    on,
    off,
    emit,
  }
}

// ============================================================
// 특화 훅: 대시보드 실시간 데이터
// ============================================================

interface DashboardRealtimeData {
  equipmentStatus?: Record<string, string>
  productionCount?: number
  alertCount?: number
}

export function useDashboardSocket(
  onUpdate: (data: DashboardRealtimeData) => void
) {
  const { on, off } = useSocket('/dashboard')

  useEffect(() => {
    const handler = (data: DashboardRealtimeData) => onUpdate(data)
    on('dashboard:update', handler)

    return () => {
      off('dashboard:update', handler)
    }
  }, [on, off, onUpdate])
}

// ============================================================
// 특화 훅: LOT 상태 실시간 변경 알림
// ============================================================

interface LotStatusChangeData {
  lotId: string
  status: string
  timestamp: string
}

export function useLotStatusSocket(
  lotId: string | null,
  onStatusChange: (data: LotStatusChangeData) => void
) {
  const { on, off } = useSocket('/lots')

  useEffect(() => {
    if (!lotId) return

    const event = `lot:${lotId}:status`
    const handler = (data: LotStatusChangeData) => onStatusChange(data)
    on(event, handler)

    return () => {
      off(event, handler)
    }
  }, [lotId, on, off, onStatusChange])
}
