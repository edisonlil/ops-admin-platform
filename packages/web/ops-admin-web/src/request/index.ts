export interface OpsAdminEnvelope<TData = unknown> {
  success: boolean;
  code: string;
  message: string;
  data?: TData;
  errors?: unknown;
  request_id?: string;
  timestamp?: string;
}

export interface OpsAdminPagination {
  page: number;
  pageSize: number;
  total: number;
}

export interface OpsAdminListData<TItem = unknown> {
  items: TItem[];
  pagination: OpsAdminPagination;
}

export function unwrapOpsAdminEnvelope<TData>(payload: OpsAdminEnvelope<TData>): TData | undefined {
  return payload.data;
}
