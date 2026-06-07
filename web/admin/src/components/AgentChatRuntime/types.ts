import type { AiAgentConversation, AiAgentMessage, AiAgentToolRunResult, AiSkillPlan, AiSkillRunResult, RuntimeTrace } from '@/api/aiStudio';

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
  skill_plan?: AiSkillPlan;
  skill_results?: AiSkillRunResult[];
  agent_tool_results?: AiAgentToolRunResult[];
}
