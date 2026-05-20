import { defineStore } from 'pinia';
import { store } from '@/store';
import {
  getAppearanceTheme,
  getEffectiveAppearanceTheme,
  getPlatformAppearanceTheme,
  getPlatformBranding,
  publishCurrentTenantAppearanceTheme,
  updatePlatformBranding,
  updateAppearanceTheme,
} from '@/api/appearance';
import projectSetting from '@/settings/projectSetting';
import { useDesignSettingStore } from '@/store/modules/designSetting';
import { useUserStore } from '@/store/modules/user';
import { createAppearanceCssVars } from '@/appearance/cssVarAdapter';
import { createLayoutConfig } from '@/appearance/layoutAdapter';
import { createNaiveThemeOverrides } from '@/appearance/naiveAdapter';
import { mergeAppearanceTokens } from '@/appearance/mergeTokens';
import { getAppearancePreset } from '@/appearance/presets';
import { resolveAppearanceTokens } from '@/appearance/resolver';
import { validateAppearanceTokens } from '@/appearance/validators';
import type {
  AppearanceStoragePayload,
  AppearanceTokens,
  LayoutTokens,
  ProjectBehaviorOverrides,
  TokenOverrides,
} from '@/appearance/types';

const APPEARANCE_VERSION = 1;
const DEFAULT_PLATFORM_NAME = 'fg-agent';
const PLATFORM_THEME_STORAGE_KEY = 'ops-admin-platform:appearance:platform-theme';
const BRANDING_NAME_STORAGE_KEY = 'ops-admin-platform:branding:platform-name';
const BRANDING_LOGO_STORAGE_KEY = 'ops-admin-platform:branding:logo-url';
const BRANDING_FONT_SIZE_STORAGE_KEY = 'ops-admin-platform:branding:platform-name-font-size';

let effectiveThemeRequest: Promise<void> | null = null;
let platformThemeRequest: Promise<void> | null = null;
let platformBrandingRequest: Promise<void> | null = null;
let effectiveThemeLoadedKey = '';
let platformThemeLoaded = false;
let platformBrandingLoaded = false;

type BackendAppearancePayload = Partial<AppearanceStoragePayload> & {
  preset_id?: string;
  token_overrides?: TokenOverrides;
  layout_overrides?: Partial<LayoutTokens>;
  project_overrides?: ProjectBehaviorOverrides;
  skin_class?: string;
};

interface LoadAppearanceOptions {
  forceRefresh?: boolean;
}

interface EditableAppearanceState {
  presetId: string;
  tokenOverrides: TokenOverrides;
  layoutOverrides: Partial<LayoutTokens>;
  projectOverrides: ProjectBehaviorOverrides;
  skinClass: string;
}

interface AppearanceState extends EditableAppearanceState {
  version: number;
  loadedStorageKey: string;
  backendThemeSource: 'tenant' | 'platform' | 'builtin' | 'local';
  backendThemeId: number | null;
  backendThemeUpdatedAt: string;
  editingThemeId: number | null;
  editingThemeName: string;
  editingThemeStatus: string;
  editingPresetId: string;
  editingTokenOverrides: TokenOverrides;
  editingLayoutOverrides: Partial<LayoutTokens>;
  editingProjectOverrides: ProjectBehaviorOverrides;
  editingSkinClass: string;
  isLoadingRemote: boolean;
  isPublishing: boolean;
  platformName: string;
  platformLogoUrl: string;
  platformNameFontSize: number;
  brandingUpdatedAt: string;
  isLoadingBranding: boolean;
  isSavingBranding: boolean;
}

function clone<T>(payload: T): T {
  return JSON.parse(JSON.stringify(payload || {}));
}

function safeParseAppearance(payload: string): Partial<AppearanceStoragePayload> | null {
  try {
    const parsed = JSON.parse(payload);
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch (error) {
    return null;
  }
}

function readCachedAppearancePayload(key: string): Partial<AppearanceStoragePayload> | null {
  if (typeof window === 'undefined') return null;

  try {
    const raw = window.localStorage.getItem(key);
    const payload = raw ? safeParseAppearance(raw) : null;
    return payload?.version === APPEARANCE_VERSION ? payload : null;
  } catch (error) {
    return null;
  }
}

function readCachedPlatformAppearance(): { appearance: EditableAppearanceState; isCached: boolean } {
  const payload = readCachedAppearancePayload(PLATFORM_THEME_STORAGE_KEY);
  return {
    appearance: normalizePayload(payload || {}),
    isCached: !!payload,
  };
}

function normalizePayload(payload: BackendAppearancePayload = {}): EditableAppearanceState {
  const presetId = payload.presetId || payload.preset_id || 'default';
  return {
    presetId,
    tokenOverrides: clone(payload.tokenOverrides || payload.token_overrides || {}),
    layoutOverrides: clone(payload.layoutOverrides || payload.layout_overrides || {}),
    projectOverrides: clone(payload.projectOverrides || payload.project_overrides || {}),
    skinClass: payload.skinClass || payload.skin_class || getAppearancePreset(presetId).skinClass || '',
  };
}

function toStoragePayload(state: EditableAppearanceState): AppearanceStoragePayload {
  return {
    version: APPEARANCE_VERSION,
    presetId: state.presetId,
    tokenOverrides: clone(state.tokenOverrides),
    layoutOverrides: clone(state.layoutOverrides),
    projectOverrides: clone(state.projectOverrides),
    skinClass: state.skinClass,
  };
}

function writeStorage(key: string, payload: AppearanceStoragePayload) {
  window.localStorage.setItem(key, JSON.stringify(payload));
}

function resolveTokensFor(state: EditableAppearanceState, darkTheme: boolean): AppearanceTokens {
  return mergeAppearanceTokens(
    getAppearancePreset(state.presetId),
    state.tokenOverrides,
    state.layoutOverrides,
    darkTheme
  );
}

function mergeProjectOverrides(overrides: ProjectBehaviorOverrides): Required<ProjectBehaviorOverrides> {
  const base = projectSetting;
  return {
    navMode: overrides.navMode || base.navMode,
    navTheme: overrides.navTheme || base.navTheme,
    headerSetting: {
      ...base.headerSetting,
      ...(overrides.headerSetting || {}),
    },
    menuSetting: {
      ...base.menuSetting,
      ...(overrides.menuSetting || {}),
    },
    multiTabsSetting: {
      ...base.multiTabsSetting,
      ...(overrides.multiTabsSetting || {}),
    },
    crumbsSetting: {
      ...base.crumbsSetting,
      ...(overrides.crumbsSetting || {}),
    },
    isPageAnimate: overrides.isPageAnimate ?? base.isPageAnimate,
    pageAnimateType: overrides.pageAnimateType || base.pageAnimateType,
  };
}

function readCachedPlatformName() {
  if (typeof window === 'undefined') return DEFAULT_PLATFORM_NAME;

  try {
    return window.localStorage.getItem(BRANDING_NAME_STORAGE_KEY) || DEFAULT_PLATFORM_NAME;
  } catch (error) {
    return DEFAULT_PLATFORM_NAME;
  }
}

function readCachedPlatformLogoUrl() {
  if (typeof window === 'undefined') return '';

  try {
    return window.localStorage.getItem(BRANDING_LOGO_STORAGE_KEY) || '';
  } catch (error) {
    return '';
  }
}

function readCachedPlatformNameFontSize() {
  if (typeof window === 'undefined') return 20;

  try {
    const value = Number(window.localStorage.getItem(BRANDING_FONT_SIZE_STORAGE_KEY) || 20);
    return Number.isFinite(value) ? value : 20;
  } catch (error) {
    return 20;
  }
}

function syncDocumentTitle(platformName: string) {
  if (typeof document === 'undefined') return;

  document.title = platformName.trim() || DEFAULT_PLATFORM_NAME;
}

function syncDocumentFavicon(logoUrl: string) {
  if (typeof document === 'undefined') return;

  const nextHref = logoUrl.trim();
  let favicon = document.querySelector<HTMLLinkElement>('link#app-favicon');
  if (!favicon) {
    favicon = document.querySelector<HTMLLinkElement>('link[rel~="icon"]');
  }
  if (!nextHref) {
    favicon?.remove();
    return;
  }
  if (!favicon) {
    favicon = document.createElement('link');
    favicon.id = 'app-favicon';
    favicon.rel = 'icon';
    document.head.appendChild(favicon);
  }

  favicon.href = nextHref;
  if (nextHref.endsWith('.svg') || nextHref.startsWith('data:image/svg+xml')) {
    favicon.type = 'image/svg+xml';
    return;
  }
  favicon.removeAttribute('type');
}

function cacheBrandingLogoUrl(logoUrl: string) {
  if (typeof window === 'undefined') return;

  const normalizedLogoUrl = logoUrl.trim();
  try {
    if (normalizedLogoUrl) {
      window.localStorage.setItem(BRANDING_LOGO_STORAGE_KEY, normalizedLogoUrl);
      return;
    }
    window.localStorage.removeItem(BRANDING_LOGO_STORAGE_KEY);
  } catch (error) {
    // Best effort only; favicon still updates for the current page.
  }
}

function cacheBrandingPlatformName(platformName: string) {
  if (typeof window === 'undefined') return;

  const normalizedPlatformName = platformName.trim();
  try {
    if (normalizedPlatformName) {
      window.localStorage.setItem(BRANDING_NAME_STORAGE_KEY, normalizedPlatformName);
      return;
    }
    window.localStorage.removeItem(BRANDING_NAME_STORAGE_KEY);
  } catch (error) {
    // Best effort only; title still updates for the current page.
  }
}

function cacheBrandingPlatformNameFontSize(platformNameFontSize: number) {
  if (typeof window === 'undefined') return;

  try {
    window.localStorage.setItem(BRANDING_FONT_SIZE_STORAGE_KEY, String(platformNameFontSize || 20));
  } catch (error) {
    // Best effort only; the current page still uses the fetched branding.
  }
}

export const useAppearanceStore = defineStore({
  id: 'app-appearance',
  state: (): AppearanceState => {
    const cachedPlatformAppearance = readCachedPlatformAppearance();
    return {
      version: APPEARANCE_VERSION,
      presetId: cachedPlatformAppearance.appearance.presetId,
      tokenOverrides: cachedPlatformAppearance.appearance.tokenOverrides,
      layoutOverrides: cachedPlatformAppearance.appearance.layoutOverrides,
      projectOverrides: cachedPlatformAppearance.appearance.projectOverrides,
      skinClass: cachedPlatformAppearance.appearance.skinClass,
      loadedStorageKey: cachedPlatformAppearance.isCached ? PLATFORM_THEME_STORAGE_KEY : '',
      backendThemeSource: cachedPlatformAppearance.isCached ? 'platform' : 'local',
      backendThemeId: null,
      backendThemeUpdatedAt: '',
      editingThemeId: null,
      editingThemeName: '',
      editingThemeStatus: '',
      editingPresetId: 'default',
      editingTokenOverrides: {},
      editingLayoutOverrides: {},
      editingProjectOverrides: {},
      editingSkinClass: '',
      isLoadingRemote: false,
      isPublishing: false,
      platformName: readCachedPlatformName(),
      platformLogoUrl: readCachedPlatformLogoUrl(),
      platformNameFontSize: readCachedPlatformNameFontSize(),
      brandingUpdatedAt: '',
      isLoadingBranding: false,
      isSavingBranding: false,
    };
  },
  getters: {
    activePreset(state) {
      return getAppearancePreset(state.presetId);
    },
    editorPreset(state) {
      return getAppearancePreset(state.editingPresetId);
    },
    currentTenantKey(): string {
      const userStore = useUserStore();
      const tenant = userStore.info?.current_tenant || {};
      return String(tenant.key || tenant.slug || tenant.id || tenant.name || 'default-tenant');
    },
    currentUsername(): string {
      const userStore = useUserStore();
      return String(userStore.info?.username || userStore.username || 'anonymous');
    },
    storageKey(): string {
      return `naive-ui-admin:appearance:${this.currentTenantKey}:${this.currentUsername}`;
    },
    tenantStorageKey(): string {
      return `naive-ui-admin:appearance:${this.currentTenantKey}:tenant-published`;
    },
    runtimeState(state): EditableAppearanceState {
      return {
        presetId: state.presetId,
        tokenOverrides: state.tokenOverrides,
        layoutOverrides: state.layoutOverrides,
        projectOverrides: state.projectOverrides,
        skinClass: state.skinClass,
      };
    },
    editorState(state): EditableAppearanceState {
      return {
        presetId: state.editingPresetId,
        tokenOverrides: state.editingTokenOverrides,
        layoutOverrides: state.editingLayoutOverrides,
        projectOverrides: state.editingProjectOverrides,
        skinClass: state.editingSkinClass,
      };
    },
    mergedTokens(): AppearanceTokens {
      const designStore = useDesignSettingStore();
      return resolveTokensFor(this.runtimeState, designStore.darkTheme);
    },
    editorMergedTokens(): AppearanceTokens {
      const designStore = useDesignSettingStore();
      return resolveTokensFor(this.editorState, designStore.darkTheme);
    },
    resolvedAppearance() {
      const resolved = resolveAppearanceTokens(this.mergedTokens);
      const validationErrors = validateAppearanceTokens(resolved.tokens);
      return {
        tokens: resolved.tokens,
        errors: [...resolved.errors, ...validationErrors],
      };
    },
    editorResolvedAppearance() {
      const resolved = resolveAppearanceTokens(this.editorMergedTokens);
      const validationErrors = validateAppearanceTokens(resolved.tokens);
      return {
        tokens: resolved.tokens,
        errors: [...resolved.errors, ...validationErrors],
      };
    },
    resolvedTokens(): AppearanceTokens {
      return this.resolvedAppearance.tokens;
    },
    editorResolvedTokens(): AppearanceTokens {
      return this.editorResolvedAppearance.tokens;
    },
    validationErrors() {
      return this.resolvedAppearance.errors;
    },
    editorValidationErrors() {
      return this.editorResolvedAppearance.errors;
    },
    themeOverrides() {
      return createNaiveThemeOverrides(this.resolvedTokens);
    },
    editorThemeOverrides() {
      return createNaiveThemeOverrides(this.editorResolvedTokens);
    },
    cssVars() {
      return createAppearanceCssVars(this.resolvedTokens);
    },
    editorCssVars() {
      return createAppearanceCssVars(this.editorResolvedTokens);
    },
    layoutConfig() {
      return createLayoutConfig(this.resolvedTokens);
    },
    editorLayoutConfig() {
      return createLayoutConfig(this.editorResolvedTokens);
    },
    projectConfig(state) {
      return mergeProjectOverrides(state.projectOverrides);
    },
    editorProjectConfig(state) {
      return mergeProjectOverrides(state.editingProjectOverrides);
    },
    effectiveSkinClass(state): string {
      return state.skinClass || this.activePreset.skinClass || '';
    },
    editorEffectiveSkinClass(state): string {
      return state.editingSkinClass || this.editorPreset.skinClass || '';
    },
    displayPlatformName(state): string {
      return state.platformName.trim() || DEFAULT_PLATFORM_NAME;
    },
    displayPlatformLogoUrl(state): string {
      return state.platformLogoUrl.trim();
    },
    displayPlatformNameFontSize(state): number {
      return Math.max(12, Math.min(32, Number(state.platformNameFontSize || 20)));
    },
  },
  actions: {
    applyPayload(payload: BackendAppearancePayload) {
      const next = normalizePayload(payload);
      this.presetId = next.presetId;
      this.tokenOverrides = next.tokenOverrides;
      this.layoutOverrides = next.layoutOverrides;
      this.projectOverrides = next.projectOverrides;
      this.skinClass = next.skinClass;
    },
    applyEditorPayload(payload: BackendAppearancePayload) {
      const next = normalizePayload(payload);
      this.editingPresetId = next.presetId;
      this.editingTokenOverrides = next.tokenOverrides;
      this.editingLayoutOverrides = next.layoutOverrides;
      this.editingProjectOverrides = next.projectOverrides;
      this.editingSkinClass = next.skinClass;
    },
    persistRuntime() {
      if (typeof window === 'undefined') return;
      this.loadedStorageKey = this.storageKey;
      writeStorage(this.storageKey, toStoragePayload(this.runtimeState));
    },
    cacheTenantPayload(payload: AppearanceStoragePayload) {
      if (typeof window === 'undefined') return;
      writeStorage(this.tenantStorageKey, payload);
    },
    cachePlatformPayload(payload: AppearanceStoragePayload) {
      if (typeof window === 'undefined') return;
      writeStorage(PLATFORM_THEME_STORAGE_KEY, payload);
    },
    clearPlatformPayload() {
      if (typeof window === 'undefined') return;
      window.localStorage.removeItem(PLATFORM_THEME_STORAGE_KEY);
    },
    invalidateRemoteCache(scope: 'all' | 'tenant-theme' | 'platform-theme' | 'branding' = 'all') {
      if (scope === 'all' || scope === 'tenant-theme') {
        effectiveThemeLoadedKey = '';
      }
      if (scope === 'all' || scope === 'platform-theme') {
        platformThemeLoaded = false;
      }
      if (scope === 'all' || scope === 'branding') {
        platformBrandingLoaded = false;
      }
    },
    reloadPlatformTheme() {
      if (typeof window === 'undefined') return;
      const raw = window.localStorage.getItem(PLATFORM_THEME_STORAGE_KEY);
      const payload = raw ? safeParseAppearance(raw) : null;

      this.loadedStorageKey = PLATFORM_THEME_STORAGE_KEY;
      if (!payload || payload.version !== APPEARANCE_VERSION) {
        this.version = APPEARANCE_VERSION;
        this.applyPayload({});
        this.backendThemeSource = 'builtin';
        this.backendThemeId = null;
        this.backendThemeUpdatedAt = '';
        return;
      }

      this.applyPayload(payload);
      this.backendThemeSource = 'platform';
      this.backendThemeId = null;
      this.backendThemeUpdatedAt = '';
    },
    reloadForCurrentTenant() {
      if (typeof window === 'undefined') return;
      const key = this.storageKey;
      const raw = window.localStorage.getItem(key) || window.localStorage.getItem(this.tenantStorageKey);
      const payload = raw ? safeParseAppearance(raw) : null;

      this.loadedStorageKey = key;
      if (!payload || payload.version !== APPEARANCE_VERSION) {
        this.version = APPEARANCE_VERSION;
        this.applyPayload({});
        this.backendThemeSource = 'local';
        this.backendThemeId = null;
        this.backendThemeUpdatedAt = '';
        return;
      }

      this.applyPayload(payload);
      this.backendThemeSource = 'local';
    },
    async loadEffectiveThemeForCurrentTenant(options: LoadAppearanceOptions = {}) {
      const cacheKey = this.storageKey;
      if (!options.forceRefresh && effectiveThemeLoadedKey === cacheKey && this.loadedStorageKey === cacheKey) return;
      if (effectiveThemeRequest) return effectiveThemeRequest;
      this.ensureLoadedForCurrentTenant();
      this.isLoadingRemote = true;
      effectiveThemeRequest = (async () => {
        const response = await getEffectiveAppearanceTheme({ forceRefresh: options.forceRefresh });
        if (this.storageKey !== cacheKey) return;
        this.loadedStorageKey = cacheKey;
        if (!response?.theme) {
          this.applyPayload({});
          this.backendThemeSource = 'builtin';
          this.backendThemeId = null;
          this.backendThemeUpdatedAt = '';
          this.clearPlatformPayload();
          effectiveThemeLoadedKey = cacheKey;
          return;
        }
        this.applyPayload(response.theme);
        this.backendThemeSource = response.source;
        this.backendThemeId = response.theme.id || null;
        this.backendThemeUpdatedAt = response.theme.update_time || '';
        this.cacheTenantPayload(toStoragePayload(this.runtimeState));
        if (response.source === 'platform') {
          this.cachePlatformPayload(toStoragePayload(this.runtimeState));
        }
        effectiveThemeLoadedKey = cacheKey;
      })();
      try {
        return await effectiveThemeRequest;
      } finally {
        effectiveThemeRequest = null;
        this.isLoadingRemote = false;
      }
    },
    async loadPlatformTheme(options: LoadAppearanceOptions = {}) {
      if (!options.forceRefresh && platformThemeLoaded && this.loadedStorageKey === PLATFORM_THEME_STORAGE_KEY) return;
      if (platformThemeRequest) return platformThemeRequest;
      this.reloadPlatformTheme();
      this.isLoadingRemote = true;
      platformThemeRequest = (async () => {
        const response = await getPlatformAppearanceTheme({ forceRefresh: options.forceRefresh });
        this.loadedStorageKey = PLATFORM_THEME_STORAGE_KEY;
        if (!response?.theme) {
          this.applyPayload({});
          this.backendThemeSource = 'builtin';
          this.backendThemeId = null;
          this.backendThemeUpdatedAt = '';
          platformThemeLoaded = true;
          return;
        }
        this.applyPayload(response.theme);
        this.backendThemeSource = response.source === 'tenant' ? 'platform' : response.source;
        this.backendThemeId = response.theme.id || null;
        this.backendThemeUpdatedAt = response.theme.update_time || '';
        this.cachePlatformPayload(toStoragePayload(this.runtimeState));
        platformThemeLoaded = true;
      })();
      try {
        return await platformThemeRequest;
      } finally {
        platformThemeRequest = null;
        this.isLoadingRemote = false;
      }
    },
    async loadPlatformBranding(options: LoadAppearanceOptions = {}) {
      if (!options.forceRefresh && platformBrandingLoaded) return;
      if (platformBrandingRequest) return platformBrandingRequest;
      this.isLoadingBranding = true;
      platformBrandingRequest = (async () => {
        const response = await getPlatformBranding({ forceRefresh: options.forceRefresh });
        const branding = response?.branding;
        if (!branding) return;
        this.platformName = branding.platformName || branding.platform_name || DEFAULT_PLATFORM_NAME;
        this.platformLogoUrl = branding.logoUrl || branding.logo_url || '';
        this.platformNameFontSize = branding.platformNameFontSize || branding.platform_name_font_size || 20;
        this.brandingUpdatedAt = branding.update_time || '';
        cacheBrandingPlatformName(this.platformName);
        cacheBrandingLogoUrl(this.platformLogoUrl);
        cacheBrandingPlatformNameFontSize(this.platformNameFontSize);
        syncDocumentTitle(this.platformName);
        syncDocumentFavicon(this.platformLogoUrl);
        platformBrandingLoaded = true;
      })();
      try {
        return await platformBrandingRequest;
      } finally {
        platformBrandingRequest = null;
        this.isLoadingBranding = false;
      }
    },
    async savePlatformBranding(payload: { platformName: string; logoUrl: string; platformNameFontSize: number }) {
      this.isSavingBranding = true;
      try {
        const response = await updatePlatformBranding({
          platformName: payload.platformName,
          logoUrl: payload.logoUrl,
          platformNameFontSize: payload.platformNameFontSize,
        });
        const branding = response?.branding;
        if (branding) {
          this.platformName = branding.platformName || branding.platform_name || DEFAULT_PLATFORM_NAME;
          this.platformLogoUrl = branding.logoUrl || branding.logo_url || '';
          this.platformNameFontSize = branding.platformNameFontSize || branding.platform_name_font_size || 20;
          this.brandingUpdatedAt = branding.update_time || '';
          cacheBrandingPlatformName(this.platformName);
          cacheBrandingLogoUrl(this.platformLogoUrl);
          cacheBrandingPlatformNameFontSize(this.platformNameFontSize);
          syncDocumentTitle(this.platformName);
          syncDocumentFavicon(this.platformLogoUrl);
          platformBrandingLoaded = true;
        }
        return response;
      } finally {
        this.isSavingBranding = false;
      }
    },
    ensureLoadedForCurrentTenant() {
      if (this.loadedStorageKey !== this.storageKey) {
        this.reloadForCurrentTenant();
      }
    },
    ensurePlatformThemeLoaded() {
      if (this.loadedStorageKey !== PLATFORM_THEME_STORAGE_KEY) {
        this.reloadPlatformTheme();
      }
    },
    applyPreset(presetId: string) {
      const preset = getAppearancePreset(presetId);
      this.editingPresetId = preset.id;
      this.editingTokenOverrides = {};
      this.editingLayoutOverrides = {};
      this.editingSkinClass = preset.skinClass || '';
    },
    updatePrimitiveToken(key: string, value: string) {
      this.editingTokenOverrides.primitive = {
        ...(this.editingTokenOverrides.primitive || {}),
        [key]: value,
      };
    },
    updateSemanticToken(key: string, value: string) {
      const designStore = useDesignSettingStore();
      if (designStore.darkTheme) {
        this.editingTokenOverrides.darkSemantic = {
          ...(this.editingTokenOverrides.darkSemantic || {}),
          [key]: value,
        };
        return;
      }
      this.editingTokenOverrides.semantic = {
        ...(this.editingTokenOverrides.semantic || {}),
        [key]: value,
      };
    },
    updateComponentToken(component: string, key: string, value: string) {
      this.editingTokenOverrides.component = {
        ...(this.editingTokenOverrides.component || {}),
        [component]: {
          ...((this.editingTokenOverrides.component || {})[component] || {}),
          [key]: value,
        },
      };
    },
    updateLayoutToken(key: keyof LayoutTokens, value: LayoutTokens[keyof LayoutTokens]) {
      this.editingLayoutOverrides = {
        ...this.editingLayoutOverrides,
        [key]: value,
      };
    },
    updateProjectOverride(section: keyof ProjectBehaviorOverrides, value: any) {
      this.editingProjectOverrides = {
        ...this.editingProjectOverrides,
        [section]: value,
      };
    },
    updateNestedProjectOverride(section: keyof ProjectBehaviorOverrides, key: string, value: any) {
      this.editingProjectOverrides = {
        ...this.editingProjectOverrides,
        [section]: {
          ...((this.editingProjectOverrides[section] as Record<string, any>) || {}),
          [key]: value,
        },
      };
    },
    resetToPreset() {
      const preset = getAppearancePreset(this.editingPresetId);
      this.editingTokenOverrides = {};
      this.editingLayoutOverrides = {};
      this.editingSkinClass = preset.skinClass || '';
    },
    resetAll() {
      this.editingPresetId = 'default';
      this.editingTokenOverrides = {};
      this.editingLayoutOverrides = {};
      this.editingProjectOverrides = {};
      this.editingSkinClass = '';
    },
    exportThemeOverridesJSON() {
      return JSON.stringify(this.editorThemeOverrides, null, 2);
    },
    exportAppearanceJSON() {
      return JSON.stringify(toStoragePayload(this.editorState), null, 2);
    },
    importAppearanceJSON(payload: string | Partial<AppearanceStoragePayload>) {
      const parsed = typeof payload === 'string' ? safeParseAppearance(payload) : payload;
      if (!parsed) {
        throw new Error('外观配置 JSON 格式不正确。');
      }
      this.applyEditorPayload(parsed);
    },
    async publishCurrentTenantTheme() {
      this.isPublishing = true;
      try {
        const response = await publishCurrentTenantAppearanceTheme({
          name: '当前租户主题',
          ...toStoragePayload(this.runtimeState),
        });
        if (response?.theme) {
          this.applyPayload(response.theme);
          this.backendThemeSource = response.source;
          this.backendThemeId = response.theme.id || null;
          this.backendThemeUpdatedAt = response.theme.update_time || '';
          this.persistRuntime();
          this.cacheTenantPayload(toStoragePayload(this.runtimeState));
          effectiveThemeLoadedKey = this.storageKey;
        }
        return response;
      } finally {
        this.isPublishing = false;
      }
    },
    async loadThemeDraft(themeId: number) {
      this.isLoadingRemote = true;
      try {
        const response = await getAppearanceTheme(themeId);
        const theme = response?.item;
        if (!theme) return;
        this.editingThemeId = theme.id || themeId;
        this.editingThemeName = theme.name || '';
        this.editingThemeStatus = theme.status || '';
        this.applyEditorPayload(theme.draft || theme);
      } finally {
        this.isLoadingRemote = false;
      }
    },
    async saveEditingThemeDraft() {
      if (!this.editingThemeId) return null;
      this.isPublishing = true;
      try {
        const response = await updateAppearanceTheme(this.editingThemeId, {
          name: this.editingThemeName || '未命名主题',
          ...toStoragePayload(this.editorState),
        });
        if (response?.item) {
          this.editingThemeName = response.item.name || this.editingThemeName;
          this.editingThemeStatus = response.item.status || this.editingThemeStatus;
          this.applyEditorPayload(response.item.draft || response.item);
          this.invalidateRemoteCache('all');
        }
        return response;
      } finally {
        this.isPublishing = false;
      }
    },
    clearEditingTheme() {
      this.editingThemeId = null;
      this.editingThemeName = '';
      this.editingThemeStatus = '';
      this.applyEditorPayload({});
    },
  },
});

export function useAppearance() {
  return useAppearanceStore(store);
}
