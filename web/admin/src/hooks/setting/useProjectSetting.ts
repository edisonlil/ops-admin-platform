import { computed } from 'vue';
import { useProjectSettingStore } from '@/store/modules/projectSetting';
import { useAppearanceStore } from '@/store/modules/appearance';

export function useProjectSetting() {
  const projectStore = useProjectSettingStore();
  const appearanceStore = useAppearanceStore();

  const navMode = computed(() => appearanceStore.projectConfig.navMode || projectStore.navMode);

  const navTheme = computed(() => appearanceStore.projectConfig.navTheme || projectStore.navTheme);

  const isMobile = computed(() => projectStore.isMobile);

  const headerSetting = computed(() => appearanceStore.projectConfig.headerSetting || projectStore.headerSetting);

  const multiTabsSetting = computed(() => appearanceStore.projectConfig.multiTabsSetting || projectStore.multiTabsSetting);

  const menuSetting = computed(() => appearanceStore.projectConfig.menuSetting || projectStore.menuSetting);

  const crumbsSetting = computed(() => appearanceStore.projectConfig.crumbsSetting || projectStore.crumbsSetting);

  const permissionMode = computed(() => projectStore.permissionMode);

  const showFooter = computed(() => projectStore.showFooter);

  const isPageAnimate = computed(() => appearanceStore.projectConfig.isPageAnimate ?? projectStore.isPageAnimate);

  const pageAnimateType = computed(() => appearanceStore.projectConfig.pageAnimateType || projectStore.pageAnimateType);

  return {
    navMode,
    navTheme,
    isMobile,
    headerSetting,
    multiTabsSetting,
    menuSetting,
    crumbsSetting,
    permissionMode,
    showFooter,
    isPageAnimate,
    pageAnimateType,
  };
}
