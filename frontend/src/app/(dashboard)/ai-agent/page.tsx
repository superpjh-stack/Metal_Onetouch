'use client'

import { useEffect, useRef, useState } from 'react'
import { Send, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { PageHeader } from '@/components/ui/page-header'
import { ChatBubble } from '@/components/ui/chat-bubble'
import { useUiStore } from '@/lib/stores/ui-store'
import {
  useQueryAgent,
  type AgentQueryResponse,
} from '@/lib/hooks/use-ai-agent'

type AgentType = 'inbound' | 'outbound'

interface LocalMessage {
  role: 'user' | 'assistant'
  content: string
  riskLevel?: 'GREEN' | 'YELLOW' | 'RED' | null
  sources?: Array<{ lot_id?: string; similarity?: number; date?: string }>
  isLoading?: boolean
}

const AGENT_TABS: { value: AgentType; label: string }[] = [
  { value: 'inbound', label: '입고 Agent' },
  { value: 'outbound', label: '출하 Agent' },
]

const PLACEHOLDER: Record<AgentType, string> = {
  inbound: '예) 현대철강 SUS304 2T 100장 입고 예정인데 품질 이슈 있을까요?',
  outbound: '예) LOT-2026-0012 출하 전 품질 리스크를 확인해주세요.',
}

export default function AiAgentPage() {
  const { setPageTitle } = useUiStore()
  const [agentType, setAgentType] = useState<AgentType>('inbound')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { setPageTitle('AI Agent') }, [setPageTitle])

  const { mutate, isPending } = useQueryAgent(agentType)

  const handleAgentTypeChange = (val: AgentType) => {
    setAgentType(val)
    setConversationId(null)
    setMessages([])
  }

  const handleSend = () => {
    if (!query.trim() || isPending) return
    const userText = query.trim()
    setQuery('')

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: userText },
      { role: 'assistant', content: '', isLoading: true },
    ])

    mutate(
      { query: userText, conversation_id: conversationId },
      {
        onSuccess: (res: AgentQueryResponse) => {
          setConversationId(res.conversation_id)
          setMessages((prev) =>
            prev.map((m, i) =>
              i === prev.length - 1
                ? {
                    role: 'assistant',
                    content: res.content,
                    riskLevel: res.risk_level,
                    sources: res.sources,
                    isLoading: false,
                  }
                : m
            )
          )
          setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
        },
        onError: () => {
          setMessages((prev) =>
            prev.map((m, i) =>
              i === prev.length - 1
                ? { role: 'assistant', content: '오류가 발생했습니다. 다시 시도해주세요.', isLoading: false }
                : m
            )
          )
        },
      }
    )
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] gap-4">
      <PageHeader
        title="AI Agent"
        description="자연어로 입고·출하 이력을 조회하고 품질 리스크를 분석합니다"
      />

      {/* 에이전트 선택 탭 */}
      <div className="flex gap-2 rounded-lg border bg-card p-1 w-fit">
        {AGENT_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => handleAgentTypeChange(tab.value)}
            className={[
              'rounded-md px-4 py-2 text-sm font-medium transition-all',
              agentType === tab.value
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:bg-accent hover:text-foreground',
            ].join(' ')}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 채팅 영역 */}
      <div className="flex-1 overflow-y-auto rounded-xl border bg-card p-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
            <p className="text-sm">
              {agentType === 'inbound' ? '입고' : '출하'} 관련 질문을 입력하세요
            </p>
            <p className="text-xs opacity-60">{PLACEHOLDER[agentType]}</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <ChatBubble
            key={i}
            role={msg.role}
            content={msg.content}
            isLoading={msg.isLoading}
            riskLevel={msg.riskLevel}
            sources={msg.sources}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* 입력 영역 */}
      <div className="flex gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={PLACEHOLDER[agentType]}
          disabled={isPending}
          className="flex-1"
        />
        <Button onClick={handleSend} disabled={!query.trim() || isPending}>
          {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          전송
        </Button>
      </div>
    </div>
  )
}
