'use client'

import { cn } from '@/lib/utils'
import { RiskBadge } from './risk-badge'

interface ChatSource {
  lot_id?: string
  similarity?: number
  date?: string
}

interface ChatBubbleProps {
  role: 'user' | 'assistant'
  content: string
  riskLevel?: 'GREEN' | 'YELLOW' | 'RED' | null
  sources?: ChatSource[]
  isLoading?: boolean
  createdAt?: string
}

export function ChatBubble({
  role,
  content,
  riskLevel,
  sources = [],
  isLoading = false,
  createdAt,
}: ChatBubbleProps) {
  const isUser = role === 'user'

  if (isLoading) {
    return (
      <div className="flex justify-start mb-4">
        <div className="max-w-[80%] rounded-2xl rounded-tl-sm px-4 py-3 bg-muted">
          <div className="flex gap-1.5 items-center h-5">
            <span className="w-2 h-2 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:0ms]" />
            <span className="w-2 h-2 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:150ms]" />
            <span className="w-2 h-2 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:300ms]" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('flex mb-4', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[80%] rounded-2xl px-4 py-3 space-y-2',
          isUser
            ? 'bg-primary text-primary-foreground rounded-tr-sm'
            : 'bg-muted text-foreground rounded-tl-sm'
        )}
      >
        <p className="text-sm whitespace-pre-wrap leading-relaxed">{content}</p>

        {riskLevel && (
          <div className="pt-1">
            <RiskBadge level={riskLevel} showLabel />
          </div>
        )}

        {sources.length > 0 && (
          <div className="pt-1 border-t border-border/30 space-y-1">
            <p className="text-xs text-muted-foreground font-medium">참조 이력</p>
            {sources.slice(0, 3).map((src, i) => (
              <p key={i} className="text-xs text-muted-foreground">
                {src.lot_id && `LOT: ${src.lot_id}`}
                {src.similarity !== undefined && ` (유사도 ${(src.similarity * 100).toFixed(0)}%)`}
                {src.date && ` · ${src.date}`}
              </p>
            ))}
          </div>
        )}

        {createdAt && (
          <p className={cn('text-xs', isUser ? 'text-primary-foreground/60' : 'text-muted-foreground')}>
            {createdAt}
          </p>
        )}
      </div>
    </div>
  )
}
