<template>
  <div class="platform-page">
    <div class="platform-page__header">
      <div>
        <h1>平台管理</h1>
        <p>维护平台基础标识。Logo 留空时，侧栏仅展示平台名称。</p>
      </div>
      <n-button :loading="appearanceStore.isLoadingBranding" @click="loadBranding">刷新</n-button>
    </div>

    <n-card :bordered="false" class="platform-branding">
      <div class="platform-branding__layout">
        <section class="platform-branding__preview" aria-label="平台标识预览">
          <div class="platform-branding__shell">
            <img v-if="logoPreview" :src="logoPreview" :alt="brandingForm.platformName" />
            <strong :style="{ fontSize: `${brandingForm.platformNameFontSize}px` }">
              {{ brandingForm.platformName || 'fg-agent' }}
            </strong>
          </div>
        </section>

        <n-form class="platform-branding__form" label-placement="top">
          <n-form-item label="平台名称" path="platformName">
            <n-input v-model:value="brandingForm.platformName" maxlength="80" placeholder="fg-agent" clearable />
          </n-form-item>
          <n-form-item label="平台 Logo" path="logoUrl">
            <n-input v-model:value="brandingForm.logoUrl" placeholder="https://example.com/logo.svg" clearable />
          </n-form-item>
          <n-form-item label="名称字号" path="platformNameFontSize">
            <n-input-number
              v-model:value="brandingForm.platformNameFontSize"
              :min="12"
              :max="32"
              :step="1"
              style="width: 160px"
            />
          </n-form-item>
          <n-space justify="end">
            <n-button v-if="canUpdateBranding" @click="clearLogo">清空 Logo</n-button>
            <n-button v-if="canUpdateBranding" type="primary" :loading="appearanceStore.isSavingBranding" @click="saveBranding">
              保存
            </n-button>
          </n-space>
        </n-form>
      </div>
    </n-card>
  </div>
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive } from 'vue';
  import { useAppearanceStore } from '@/store/modules/appearance';
  import { usePermission } from '@/hooks/web/usePermission';

  const appearanceStore = useAppearanceStore();
  const { hasPermission } = usePermission();
  const brandingForm = reactive({
    platformName: 'fg-agent',
    logoUrl: '',
    platformNameFontSize: 20,
  });
  const logoPreview = computed(() => brandingForm.logoUrl.trim());
  const canUpdateBranding = computed(() => hasPermission(['platform:branding:update']));

  function syncForm() {
    brandingForm.platformName = appearanceStore.displayPlatformName;
    brandingForm.logoUrl = appearanceStore.displayPlatformLogoUrl;
    brandingForm.platformNameFontSize = appearanceStore.displayPlatformNameFontSize;
  }

  async function loadBranding() {
    await appearanceStore.loadPlatformBranding();
    syncForm();
  }

  function clearLogo() {
    brandingForm.logoUrl = '';
  }

  async function saveBranding() {
    await appearanceStore.savePlatformBranding({
      platformName: brandingForm.platformName,
      logoUrl: brandingForm.logoUrl,
      platformNameFontSize: brandingForm.platformNameFontSize,
    });
    syncForm();
    window.$message?.success('平台标识已保存');
  }

  onMounted(loadBranding);
</script>

<style lang="less" scoped>
  .platform-page {
    display: grid;
    gap: 16px;
    padding: var(--app-content-padding);

    &__header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;

      h1 {
        margin: 0;
        color: var(--app-text-color);
        font-size: 22px;
        font-weight: 650;
        line-height: 30px;
      }

      p {
        margin: 4px 0 0;
        color: var(--app-icon-color);
        line-height: 22px;
      }
    }
  }

  .platform-branding {
    max-width: 960px;

    &__layout {
      display: grid;
      grid-template-columns: 300px minmax(0, 1fr);
      gap: 24px;
      align-items: stretch;
    }

    &__preview {
      display: grid;
      align-items: center;
      min-height: 180px;
      padding: 18px;
      background: var(--app-page-bg);
      border: 1px solid var(--app-border-color);
      border-radius: 8px;
    }

    &__shell {
      display: flex;
      align-items: center;
      min-width: 0;
      height: 64px;
      padding: 0 18px;
      overflow: hidden;
      background: var(--app-surface-bg);
      border: 1px solid var(--app-border-color);
      border-radius: 8px;

      img {
        flex: 0 0 auto;
        max-width: 48px;
        height: 36px;
        margin-right: 12px;
        object-fit: contain;
      }

      strong {
        min-width: 0;
        overflow: hidden;
        color: var(--app-text-color);
        font-size: 20px;
        font-weight: 650;
        line-height: 28px;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    &__form {
      min-width: 0;
    }

    @media (max-width: 760px) {
      &__layout {
        grid-template-columns: 1fr;
      }
    }
  }
</style>
