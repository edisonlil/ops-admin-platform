import type { AiAgentConversation, AiAgentMessage, RuntimeTrace } from '@/api/aiStudio';

export type AgentConversation = AiAgentConversation;
export type AgentMessage = AiAgentMessage;

export interface AgentStreamMeta {
  trace_id?: string;
  model?: string;
  conversation_key?: string;
  user_message_key?: string;
  assistant_message_key?: string;
}

export interface AgentTraceState {
  trace_id: string;
  trace?: RuntimeTrace;
}
