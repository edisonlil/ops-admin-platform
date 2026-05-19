import { Alova } from '@/utils/http/alova/index';

export interface MessagingPagination {
  page: number;
  page_size: number;
  total: number;
}

export interface MessageIntent {
  id: number;
  tenant_id: number;
  message_type: string;
  priority: string;
  title: string;
  content: string;
  payload?: Record<string, unknown>;
  sender_user_id?: number | null;
  sender_name?: string;
  target_scope?: string;
  target?: Record<string, unknown>;
  status: string;
  create_time?: string;
  update_time?: string;
}

export interface MessageRecipient {
  id: number;
  tenant_id: number;
  message_id: number;
  recipient_user_id: number;
  recipient_name?: string;
  read_status: 'unread' | 'read' | string;
  read_time?: string | null;
  archive_status?: string;
  pin_status?: string;
  delivery_summary?: Record<string, unknown>;
  title: string;
  content: string;
  message_type: string;
  priority: string;
  create_time?: string;
  update_time?: string;
}

export interface MessageListData<TItem> {
  items: TItem[];
  pagination: MessagingPagination;
}

export interface MessageTemplate {
  id: number;
  tenant_id: number;
  template_key: string;
  name: string;
  description: string;
  channels: string[];
  title_template: string;
  content_template: string;
  variables_schema?: Record<string, unknown>;
  status: string;
  create_time?: string;
  update_time?: string;
}

export interface MessageChannelAccount {
  id: number;
  tenant_id: number;
  channel: string;
  name: string;
  config?: Record<string, unknown>;
  secret_ref?: string;
  enabled: boolean;
  is_default: boolean;
  create_time?: string;
  update_time?: string;
}

export type MessageChatBotPlatform = 'wps' | 'wecom' | 'feishu' | 'dingtalk' | string;

export interface MessageChatBot {
  id: number;
  tenant_id: number;
  platform: MessageChatBotPlatform;
  name: string;
  description: string;
  webhook_url: string;
  signing_secret?: string;
  message_format: 'text' | string;
  enabled: boolean;
  is_default: boolean;
  last_test_status?: string;
  last_test_message?: string;
  last_test_time?: string | null;
  create_time?: string;
  update_time?: string;
}

export interface SendInAppMessagePayload {
  title: string;
  content: string;
  recipient_user_ids: number[];
  chat_bot_ids?: number[];
  message_type?: string;
  priority?: string;
  payload?: Record<string, unknown>;
}

export interface SendTemplateMessagePayload {
  template_key: string;
  variables: Record<string, unknown>;
  recipient_user_ids: number[];
  chat_bot_ids?: number[];
  message_type?: string;
  priority?: string;
  channels?: string[];
  payload?: Record<string, unknown>;
}

export interface RenderMessageTemplatePayload {
  template_key: string;
  variables: Record<string, unknown>;
}

export interface RenderMessageTemplateResult {
  template: MessageTemplate;
  rendered: {
    title: string;
    content: string;
    missing_variables: string[];
  };
  missing_variables: string[];
}

function withNoCacheParams<T extends Record<string, unknown>>(params: T = {} as T) {
  return {
    ...params,
    _t: Date.now(),
  };
}

export interface SortParams {
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
}

export function getMessagingInbox(params: { page?: number; page_size?: number } & SortParams = {}) {
  return Alova.Get<MessageListData<MessageRecipient>>('/messaging/inbox', {
    params: withNoCacheParams(params),
  });
}

export function getMessagingUnreadCount() {
  return Alova.Get<{ count: number }>('/messaging/inbox/unread-count', {
    params: withNoCacheParams(),
  });
}

export function markMessagingRead(recipientId: number) {
  return Alova.Post<{ item: MessageRecipient }>(`/messaging/inbox/${recipientId}/read`);
}

export function markAllMessagingRead() {
  return Alova.Post<{ updated: number }>('/messaging/inbox/read-all');
}

export function getMessagingMessages(params: { page?: number; page_size?: number } & SortParams = {}) {
  return Alova.Get<MessageListData<MessageIntent>>('/messaging/messages', {
    params: withNoCacheParams(params),
  });
}

export function sendInAppMessage(payload: SendInAppMessagePayload) {
  return Alova.Post<{ item: MessageIntent }>('/messaging/messages/send', payload);
}

export function sendTemplateMessage(payload: SendTemplateMessagePayload) {
  return Alova.Post<{ item: MessageIntent; rendered: RenderMessageTemplateResult['rendered']; channels: string[] }>(
    '/messaging/messages/send-template',
    payload
  );
}

export function getMessageTemplates(params: SortParams = {}) {
  return Alova.Get<{ items: MessageTemplate[] }>('/messaging/templates', {
    params: withNoCacheParams(params),
  });
}

export function renderMessageTemplate(payload: RenderMessageTemplatePayload) {
  return Alova.Post<RenderMessageTemplateResult>('/messaging/templates/render', payload);
}

export function saveMessageTemplate(payload: Partial<MessageTemplate>) {
  if (payload.id) {
    return Alova.Put<{ item: MessageTemplate }>(`/messaging/templates/${payload.id}`, payload);
  }
  return Alova.Post<{ item: MessageTemplate }>('/messaging/templates', payload);
}

export function enableMessageTemplate(templateId: number) {
  return Alova.Post<{ item: MessageTemplate }>(`/messaging/templates/${templateId}/enable`);
}

export function disableMessageTemplate(templateId: number) {
  return Alova.Post<{ item: MessageTemplate }>(`/messaging/templates/${templateId}/disable`);
}

export function getMessageChannelAccounts(params: SortParams = {}) {
  return Alova.Get<{ items: MessageChannelAccount[] }>('/messaging/channel-accounts', {
    params: withNoCacheParams(params),
  });
}

export function saveMessageChannelAccount(payload: Partial<MessageChannelAccount>) {
  if (payload.id) {
    return Alova.Put<{ item: MessageChannelAccount }>(`/messaging/channel-accounts/${payload.id}`, payload);
  }
  return Alova.Post<{ item: MessageChannelAccount }>('/messaging/channel-accounts', payload);
}

export function enableMessageChannelAccount(accountId: number) {
  return Alova.Post<{ item: MessageChannelAccount }>(`/messaging/channel-accounts/${accountId}/enable`);
}

export function disableMessageChannelAccount(accountId: number) {
  return Alova.Post<{ item: MessageChannelAccount }>(`/messaging/channel-accounts/${accountId}/disable`);
}

export function testMessageChannelAccount(accountId: number) {
  return Alova.Post<{ ok: boolean; channel: string; message: string }>(`/messaging/channel-accounts/${accountId}/test`);
}

export function getMessageChatBots(params: SortParams = {}) {
  return Alova.Get<{ items: MessageChatBot[] }>('/messaging/chat-bots', {
    params: withNoCacheParams(params),
  });
}

export function saveMessageChatBot(payload: Partial<MessageChatBot>) {
  if (payload.id) {
    return Alova.Put<{ item: MessageChatBot }>(`/messaging/chat-bots/${payload.id}`, payload);
  }
  return Alova.Post<{ item: MessageChatBot }>('/messaging/chat-bots', payload);
}

export function enableMessageChatBot(chatBotId: number) {
  return Alova.Post<{ item: MessageChatBot }>(`/messaging/chat-bots/${chatBotId}/enable`);
}

export function disableMessageChatBot(chatBotId: number) {
  return Alova.Post<{ item: MessageChatBot }>(`/messaging/chat-bots/${chatBotId}/disable`);
}

export function testMessageChatBot(chatBotId: number) {
  return Alova.Post<{ item: MessageChatBot; ok: boolean; message: string; status_code: number; response: Record<string, unknown> }>(
    `/messaging/chat-bots/${chatBotId}/test`
  );
}
