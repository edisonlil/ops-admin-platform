import { Alova } from '@/utils/http/alova/index';
import type { AppearanceStoragePayload } from '@/appearance/types';

export interface EffectiveAppearanceTheme {
  source: 'tenant' | 'platform' | 'builtin';
  theme: (AppearanceStoragePayload & {
    id?: number;
    tenant_id?: number;
    name?: string;
    status?: string;
    preset_id?: string;
    token_overrides?: AppearanceStoragePayload['tokenOverrides'];
    layout_overrides?: AppearanceStoragePayload['layoutOverrides'];
    project_overrides?: AppearanceStoragePayload['projectOverrides'];
    skin_class?: string;
    draft?: AppearanceStoragePayload;
    tenant_assignment_count?: number;
    is_platform_default?: boolean;
    create_time?: string;
    update_time?: string;
  }) | null;
}

export interface PublishAppearanceThemePayload extends AppearanceStoragePayload {
  name: string;
}

export interface PlatformBranding {
  platform_name?: string;
  platformName: string;
  logo_url?: string;
  logoUrl: string;
  platform_name_font_size?: number;
  platformNameFontSize: number;
  updated_by?: string;
  update_time?: string;
}

function withNoCacheParams() {
  return { _t: Date.now() };
}

export function getEffectiveAppearanceTheme() {
  return Alova.Get<EffectiveAppearanceTheme>('/appearance/effective-theme', {
    params: withNoCacheParams(),
  });
}

export function getPlatformAppearanceTheme() {
  return Alova.Get<EffectiveAppearanceTheme>('/appearance/platform-theme', {
    params: withNoCacheParams(),
  });
}

export function getPlatformBranding() {
  return Alova.Get<{ branding: PlatformBranding }>('/appearance/platform-branding', {
    params: withNoCacheParams(),
  });
}

export function updatePlatformBranding(
  payload: Pick<PlatformBranding, 'platformName' | 'logoUrl' | 'platformNameFontSize'>
) {
  return Alova.Put<{ branding: PlatformBranding }>('/appearance/platform-branding', payload);
}

export function publishCurrentTenantAppearanceTheme(payload: PublishAppearanceThemePayload) {
  return Alova.Put<EffectiveAppearanceTheme>('/appearance/tenant-theme', payload);
}

export function getAppearanceThemes() {
  return Alova.Get<{ items: NonNullable<EffectiveAppearanceTheme['theme']>[] }>('/appearance/themes', {
    params: withNoCacheParams(),
  });
}

export function createAppearanceTheme(payload: PublishAppearanceThemePayload) {
  return Alova.Post<{ item: NonNullable<EffectiveAppearanceTheme['theme']> }>('/appearance/themes', payload);
}

export function getAppearanceTheme(themeId: number) {
  return Alova.Get<{ item: NonNullable<EffectiveAppearanceTheme['theme']> }>(`/appearance/themes/${themeId}`, {
    params: withNoCacheParams(),
  });
}

export function updateAppearanceTheme(themeId: number, payload: PublishAppearanceThemePayload) {
  return Alova.Put<{ item: NonNullable<EffectiveAppearanceTheme['theme']> }>(`/appearance/themes/${themeId}`, payload);
}

export function publishAppearanceTheme(themeId: number) {
  return Alova.Post<{ item: NonNullable<EffectiveAppearanceTheme['theme']> }>(`/appearance/themes/${themeId}/publish`);
}

export function disableAppearanceTheme(themeId: number) {
  return Alova.Post<{ item: NonNullable<EffectiveAppearanceTheme['theme']> }>(`/appearance/themes/${themeId}/disable`);
}

export function setPlatformDefaultAppearanceTheme(themeId: number) {
  return Alova.Post<{ item: NonNullable<EffectiveAppearanceTheme['theme']> }>(
    `/appearance/themes/${themeId}/platform-default`
  );
}

export function getTenantAppearanceTheme(tenantId: number) {
  return Alova.Get<{ theme: EffectiveAppearanceTheme['theme'] }>(`/appearance/tenants/${tenantId}/theme`, {
    params: withNoCacheParams(),
  });
}

export function assignTenantAppearanceTheme(tenantId: number, themeId: number | null) {
  return Alova.Put<{ theme: EffectiveAppearanceTheme['theme'] }>(`/appearance/tenants/${tenantId}/theme`, {
    theme_id: themeId,
  });
}
