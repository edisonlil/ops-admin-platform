<template>
  <n-collapse default-expanded-names="navigation">
    <n-collapse-item title="导航行为" name="navigation">
      <TokenSelectRow
        label="导航栏模式"
        token-path="project.navMode"
        :model-value="projectConfig.navMode"
        :options="navModeOptions"
        @update:model-value="setNavMode"
      />
      <TokenSelectRow
        label="导航栏风格"
        token-path="project.navTheme"
        :model-value="projectConfig.navTheme"
        :options="navThemeOptions"
        @update:model-value="setNavTheme"
      />
      <SettingSwitchRow
        label="分割菜单"
        setting-path="project.menuSetting.mixMenu"
        :model-value="projectConfig.menuSetting.mixMenu"
        :disabled="projectConfig.navMode !== 'horizontal-mix'"
        @update:model-value="setMixMenu"
      />
    </n-collapse-item>

    <n-collapse-item title="壳层固定" name="fixed">
      <SettingSwitchRow
        label="固定顶栏"
        setting-path="project.headerSetting.fixed"
        :model-value="projectConfig.headerSetting.fixed"
        @update:model-value="(value) => appearanceStore.updateNestedProjectOverride('headerSetting', 'fixed', value)"
      />
      <SettingSwitchRow
        label="固定多页签"
        setting-path="project.multiTabsSetting.fixed"
        :model-value="projectConfig.multiTabsSetting.fixed"
        @update:model-value="(value) => appearanceStore.updateNestedProjectOverride('multiTabsSetting', 'fixed', value)"
      />
    </n-collapse-item>

    <n-collapse-item title="界面显示" name="display">
      <SettingSwitchRow
        label="显示重载按钮"
        setting-path="project.headerSetting.isReload"
        :model-value="projectConfig.headerSetting.isReload"
        @update:model-value="(value) => appearanceStore.updateNestedProjectOverride('headerSetting', 'isReload', value)"
      />
      <SettingSwitchRow
        label="显示面包屑"
        setting-path="project.crumbsSetting.show"
        :model-value="projectConfig.crumbsSetting.show"
        @update:model-value="(value) => appearanceStore.updateNestedProjectOverride('crumbsSetting', 'show', value)"
      />
      <SettingSwitchRow
        label="显示面包屑图标"
        setting-path="project.crumbsSetting.showIcon"
        :model-value="projectConfig.crumbsSetting.showIcon"
        :disabled="!projectConfig.crumbsSetting.show"
        @update:model-value="(value) => appearanceStore.updateNestedProjectOverride('crumbsSetting', 'showIcon', value)"
      />
      <SettingSwitchRow
        label="显示多页签"
        setting-path="project.multiTabsSetting.show"
        :model-value="projectConfig.multiTabsSetting.show"
        @update:model-value="(value) => appearanceStore.updateNestedProjectOverride('multiTabsSetting', 'show', value)"
      />
    </n-collapse-item>

    <n-collapse-item title="页面动画" name="animation">
      <SettingSwitchRow
        label="启用动画"
        setting-path="project.isPageAnimate"
        :model-value="projectConfig.isPageAnimate"
        @update:model-value="(value) => appearanceStore.updateProjectOverride('isPageAnimate', value)"
      />
      <TokenSelectRow
        label="动画类型"
        token-path="project.pageAnimateType"
        :model-value="projectConfig.pageAnimateType"
        :options="animateOptions"
        @update:model-value="(value) => appearanceStore.updateProjectOverride('pageAnimateType', value)"
      />
    </n-collapse-item>
  </n-collapse>
</template>

<script lang="ts" setup>
  import { computed } from 'vue';
  import { useAppearanceStore } from '@/store/modules/appearance';
  import SettingSwitchRow from './SettingSwitchRow.vue';
  import TokenSelectRow from './TokenSelectRow.vue';

  const appearanceStore = useAppearanceStore();
  const projectConfig = computed(() => appearanceStore.editorProjectConfig);

  const navModeOptions = [
    { label: '左侧菜单', value: 'vertical' },
    { label: '顶部菜单', value: 'horizontal' },
    { label: '顶部混合', value: 'horizontal-mix' },
  ];

  const navThemeOptions = [
    { label: '深色侧栏', value: 'dark' },
    { label: '浅色侧栏', value: 'light' },
    { label: '深色顶栏', value: 'header-dark' },
  ];

  const animateOptions = [
    { value: 'zoom-fade', label: '渐变' },
    { value: 'zoom-out', label: '闪现' },
    { value: 'fade-slide', label: '滑动' },
    { value: 'fade', label: '淡出' },
    { value: 'fade-bottom', label: '底部淡出' },
    { value: 'fade-scale', label: '缩放淡出' },
  ];

  function setNavMode(mode: string) {
    appearanceStore.updateProjectOverride('navMode', mode);
    if (mode !== 'horizontal-mix') {
      appearanceStore.updateNestedProjectOverride('menuSetting', 'mixMenu', false);
    }
  }

  function setNavTheme(theme: string) {
    let nextTheme = theme;
    if (projectConfig.value.navMode === 'horizontal' && theme === 'light') {
      nextTheme = 'dark';
    }
    appearanceStore.updateProjectOverride('navTheme', nextTheme);
  }

  function setMixMenu(value: boolean) {
    appearanceStore.updateNestedProjectOverride(
      'menuSetting',
      'mixMenu',
      projectConfig.value.navMode === 'horizontal-mix' ? value : false
    );
  }
</script>
