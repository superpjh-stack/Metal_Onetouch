'use client'
import * as React from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'

// ============================================================
// 제네릭 DataTable 컴포넌트
// ============================================================

export interface Column<T> {
  key: keyof T | string
  header: string
  cell?: (row: T) => React.ReactNode
  className?: string
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  isLoading?: boolean
  onRowClick?: (row: T) => void
  emptyMessage?: string
  toolbar?: React.ReactNode
}

export function DataTable<T extends { id: string }>({
  columns,
  data,
  isLoading,
  onRowClick,
  emptyMessage = '데이터가 없습니다',
  toolbar,
}: DataTableProps<T>) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {toolbar && <div>{toolbar}</div>}
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full rounded-md" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {toolbar && <div>{toolbar}</div>}
      <div className="rounded-lg border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40">
              {columns.map((col) => (
                <TableHead key={String(col.key)} className={col.className}>
                  {col.header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center text-muted-foreground text-sm"
                >
                  {emptyMessage}
                </TableCell>
              </TableRow>
            ) : (
              data.map((row) => (
                <TableRow
                  key={row.id}
                  onClick={() => onRowClick?.(row)}
                  className={
                    onRowClick
                      ? 'cursor-pointer hover:bg-accent/50 transition-colors'
                      : ''
                  }
                >
                  {columns.map((col) => (
                    <TableCell key={String(col.key)} className={col.className}>
                      {col.cell
                        ? col.cell(row)
                        : String(
                            (row as Record<string, unknown>)[String(col.key)] ??
                              '-'
                          )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
