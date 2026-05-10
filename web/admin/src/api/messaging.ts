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

export interface SendInAppMessagePayload {
  title: string;
  content: string;
  recipient_user_ids: number[];
  message_type?: string;
  priority?: string;
  payload?: Record<string, unknown>;
}

function withNoCacheParams<T extends Record<string, unknown>>(params: T = {} as T) {
  return {
    ...params,
    _t: Date.now(),
  };
}

export function getMessagingInbox(params: { page?: number; page_size?: number } = {}) {
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

export function getMessagingMessages(params: { page?: number; page_size?: number } = {}) {
  return Alova.Get<MessageListData<MessageIntent>>('/messaging/messages', {
    params: withNoCacheParams(params),
  });
}

export function sendInAppMessage(payload: SendInAppMessagePayload) {
  return Alova.Post<{ item: MessageIntent }>('/messaging/messages/send', payload);
}
