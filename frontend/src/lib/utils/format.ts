import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format, formatDistanceToNow, parseISO } from 'date-fns'
import { ko } from 'date-fns/locale'

// ============================================================
// Tailwind 유틸리티
// ============================================================

/**
 * tailwind-merge + clsx 조합 유틸리티
 * shadcn/ui 표준 cn 함수
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

// ============================================================
// 날짜 포맷
// ============================================================

/**
 * 한국 날짜 포맷: 2026년 4월 30일
 */
export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? parseISO(date) : date
  return format(d, 'yyyy년 M월 d일', { locale: ko })
}

/**
 * 한국 날짜+시간 포맷: 2026년 4월 30일 14:30
 */
export function formatDateTime(date: Date | string): string {
  const d = typeof date === 'string' ? parseISO(date) : date
  return format(d, 'yyyy년 M월 d일 HH:mm', { locale: ko })
}

/**
 * 짧은 날짜 포맷: 04/30
 */
export function formatShortDate(date: Date | string): string {
  const d = typeof date === 'string' ? parseISO(date) : date
  return format(d, 'MM/dd', { locale: ko })
}

/**
 * ISO 날짜를 한국 상대 시간으로: "3분 전", "2시간 전"
 */
export function formatRelativeTime(date: Date | string): string {
  const d = typeof date === 'string' ? parseISO(date) : date
  return formatDistanceToNow(d, { locale: ko, addSuffix: true })
}

/**
 * API 파라미터용 날짜 포맷: 2026-04-30
 */
export function formatApiDate(date: Date): string {
  return format(date, 'yyyy-MM-dd')
}

// ============================================================
// 숫자 포맷
// ============================================================

/**
 * 천 단위 구분 숫자: 1,234,567
 */
export function formatNumber(n: number): string {
  return new Intl.NumberFormat('ko-KR').format(n)
}

/**
 * 통화 포맷: ₩1,234,567
 */
export function formatCurrency(n: number): string {
  return new Intl.NumberFormat('ko-KR', {
    style: 'currency',
    currency: 'KRW',
  }).format(n)
}

/**
 * 백분율 포맷: 98.5%
 */
export function formatPercent(n: number, decimals = 1): string {
  return `${n.toFixed(decimals)}%`
}

/**
 * 변화율 포맷: +3.2% 또는 -1.5%
 */
export function formatChange(n: number, decimals = 1): string {
  const sign = n >= 0 ? '+' : ''
  return `${sign}${n.toFixed(decimals)}%`
}

// ============================================================
// LOT ID 포맷
// ============================================================

/**
 * LOT ID 표시 포맷
 * DB 형식 'L20260430-001' → 'L20260430-001' (그대로 표시)
 * 유효성 검사 포함
 */
export function formatLotId(lotId: string): string {
  // 'L{YYYYMMDD}-{SEQ}' 패턴 검증
  const pattern = /^L\d{8}-\d{3,}$/
  if (!pattern.test(lotId)) {
    return lotId
  }
  return lotId
}

/**
 * LOT ID에서 날짜 추출: 'L20260430-001' → '2026-04-30'
 */
export function extractDateFromLotId(lotId: string): string | null {
  const match = lotId.match(/^L(\d{4})(\d{2})(\d{2})-/)
  if (!match) return null
  return `${match[1]}-${match[2]}-${match[3]}`
}

// ============================================================
// 파일 크기 포맷
// ============================================================

/**
 * 파일 크기 포맷: 1.5 MB, 234 KB
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

// ============================================================
// 기간 포맷
// ============================================================

/**
 * 분 → 시간/분 표시: 90 → '1시간 30분'
 */
export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes}분`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  if (mins === 0) return `${hours}시간`
  return `${hours}시간 ${mins}분`
}
