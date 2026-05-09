export type AppStatusTone = 'success' | 'warning' | 'error' | 'info' | 'neutral';

export interface AppStatusSemantic {
  label: string;
  tone: AppStatusTone;
}

export const appStatusSemanticMap: Record<string, AppStatusSemantic> = {
  enabled: { label: '启用', tone: 'success' },
  disabled: { label: '禁用', tone: 'error' },
  active: { label: '启用', tone: 'success' },
  suspended: { label: '停用', tone: 'warning' },
  valid: { label: '有效', tone: 'success' },
  revoked: { label: '已撤销', tone: 'neutral' },
  draft: { label: '草稿', tone: 'info' },
  published: { label: '已发布', tone: 'success' },
  matched: { label: '已匹配', tone: 'success' },
  pendingReview: { label: '待复核', tone: 'warning' },
  success: { label: '成功', tone: 'success' },
  failed: { label: '失败', tone: 'error' },
  system: { label: '系统', tone: 'success' },
  custom: { label: '自定义', tone: 'neutral' },
  platform: { label: '平台', tone: 'info' },
  tenant: { label: '租户', tone: 'warning' },
  assigned: { label: '已分配', tone: 'success' },
  unassigned: { label: '未分配', tone: 'neutral' },
  yes: { label: '是', tone: 'warning' },
  no: { label: '否', tone: 'neutral' },
};

export function resolveAppStatusSemantic(
  statusKey?: string,
  fallback: AppStatusSemantic = { label: statusKey || '-', tone: 'neutral' }
): AppStatusSemantic {
  if (!statusKey) {
    return fallback;
  }
  return appStatusSemanticMap[statusKey] || fallback;
}
