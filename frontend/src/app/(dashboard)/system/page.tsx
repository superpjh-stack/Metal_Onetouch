'use client'

import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { DataTable } from '@/components/ui/data-table'
import { StatusBadge } from '@/components/ui/status-badge'
import { PageHeader } from '@/components/ui/page-header'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useUiStore } from '@/lib/stores/ui-store'
import { useAuth } from '@/lib/hooks/use-auth'
import apiClient from '@/lib/api/client'
import { formatDateTime } from '@/lib/utils/format'
import { ROLE_LABELS } from '@/lib/constants'
import type { User, PaginatedResponse, Role } from '@/types'

// ============================================================
// 시스템 관리 페이지 (사용자 관리)
// ============================================================

const ROLE_OPTIONS = [
  { value: 'all', label: '전체 역할' },
  { value: 'production_manager', label: '생산 관리자' },
  { value: 'quality_inspector', label: '품질 검사원' },
  { value: 'process_engineer', label: '공정 엔지니어' },
  { value: 'executive', label: '경영진' },
  { value: 'sales_engineer', label: '영업 엔지니어' },
  { value: 'admin', label: '시스템 관리자' },
]

const STATUS_OPTIONS = [
  { value: 'all', label: '전체 상태' },
  { value: 'active', label: '활성' },
  { value: 'inactive', label: '비활성' },
]

function useUsers(params?: { role?: string; is_active?: boolean }) {
  return useQuery({
    queryKey: ['users', params],
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<User & { last_login_at?: string }>>(
          '/api/v1/users',
          { params }
        )
        .then((r) => r.data),
    staleTime: 5 * 60_000,
  })
}

export default function SystemPage() {
  const { setPageTitle } = useUiStore()
  const { isAdmin } = useAuth()
  const [roleFilter, setRoleFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  useEffect(() => {
    setPageTitle('시스템관리')
  }, [setPageTitle])

  const queryParams = {
    ...(roleFilter !== 'all' && { role: roleFilter }),
    ...(statusFilter !== 'all' && {
      is_active: statusFilter === 'active',
    }),
  }

  const { data, isLoading } = useUsers(
    Object.keys(queryParams).length > 0 ? queryParams : undefined
  )
  const users = (data?.data ?? []) as Array<
    User & { last_login_at?: string }
  >

  if (!isAdmin) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 py-20 text-center">
        <p className="text-sm text-muted-foreground">
          시스템 관리자 권한이 필요합니다.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="시스템 관리"
        description="사용자 계정, RBAC 역할 권한, 시스템 로그를 관리합니다."
      />

      {/* 필터 행 */}
      <div className="flex items-center gap-3">
        <div className="w-44">
          <Select value={roleFilter} onValueChange={setRoleFilter}>
            <SelectTrigger>
              <SelectValue placeholder="역할 선택" />
            </SelectTrigger>
            <SelectContent>
              {ROLE_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="w-36">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger>
              <SelectValue placeholder="상태 선택" />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <DataTable<User & { last_login_at?: string }>
        isLoading={isLoading}
        data={users}
        columns={[
          { key: 'name', header: '이름' },
          { key: 'email', header: '이메일' },
          {
            key: 'role',
            header: '역할',
            cell: (row) =>
              ROLE_LABELS[row.role as Role] ?? row.role,
          },
          {
            key: 'department',
            header: '부서',
            cell: (row) => row.department ?? '-',
          },
          {
            key: 'isActive',
            header: '상태',
            cell: (row) => (
              <StatusBadge
                status={row.isActive ? 'completed' : 'cancelled'}
                label={row.isActive ? '활성' : '비활성'}
              />
            ),
          },
          {
            key: 'last_login_at',
            header: '마지막 로그인',
            cell: (row) =>
              row.last_login_at ? formatDateTime(row.last_login_at) : '-',
          },
        ]}
      />
    </div>
  )
}
