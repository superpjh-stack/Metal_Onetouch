import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'

export interface AIMessage {
  id: string
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  metadata: Record<string, unknown> | null
  tokens_used: number | null
  latency_ms: number | null
  created_at: string
}

export interface AIConversation {
  id: string
  agent_type: 'inbound' | 'outbound' | 'integrated'
  title: string | null
  created_at: string
  updated_at: string
}

export interface AgentQueryRequest {
  query: string
  conversation_id?: string | null
}

export interface AgentQueryResponse {
  conversation_id: string
  message_id: string
  content: string
  risk_level: 'GREEN' | 'YELLOW' | 'RED' | null
  sources: Array<{ lot_id?: string; similarity?: number; date?: string }>
  latency_ms: number
  tokens_used: number
}

export function useConversations(agentType?: string) {
  return useQuery({
    queryKey: ['ai-conversations', agentType],
    queryFn: () =>
      apiClient
        .get<AIConversation[]>('/api/v1/ai-agent/conversations', {
          params: agentType ? { agent_type: agentType } : undefined,
        })
        .then((r) => r.data),
  })
}

export function useConversationMessages(conversationId: string | null) {
  return useQuery({
    queryKey: ['ai-messages', conversationId],
    queryFn: () =>
      apiClient
        .get<AIMessage[]>(`/api/v1/ai-agent/conversations/${conversationId}/messages`)
        .then((r) => r.data),
    enabled: !!conversationId,
  })
}

export function useQueryAgent(agentType: 'inbound' | 'outbound') {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: AgentQueryRequest) =>
      apiClient
        .post<AgentQueryResponse>(`/api/v1/ai-agent/${agentType}`, body)
        .then((r) => r.data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['ai-conversations'] })
      qc.invalidateQueries({ queryKey: ['ai-messages', data.conversation_id] })
    },
  })
}
