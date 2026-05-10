import * as NaiveUI from 'naive-ui';
import { computed } from 'vue';
import { useDesignSetting } from '@/store/modules/designSetting';
import { useAppearanceStore } from '@/store/modules/appearance';

/**
 * 挂载 Naive-ui 脱离上下文的 API
 * 如果你想在 setup 外使用 useDialog、useMessage、useNotification、useLoadingBar，可以通过 createDiscreteApi 来构建对应的 API。
 * https://www.naiveui.com/zh-CN/dark/components/discrete
 */

export function setupNaiveDiscreteApi() {
  const designStore = useDesignSetting();
  const appearanceStore = useAppearanceStore();

  const configProviderPropsRef = computed(() => ({
    theme: designStore.darkTheme ? NaiveUI.darkTheme : undefined,
    themeOverrides: appearanceStore.themeOverrides,
  }));
  const { message, dialog, notification, loadingBar } = NaiveUI.createDiscreteApi(
    ['message', 'dialog', 'notification', 'loadingBar'],
    {
      configProviderProps: configProviderPropsRef,
    }
  );

  window['$message'] = message;
  window['$dialog'] = dialog;
  window['$notification'] = notification;
  window['$loading'] = loadingBar;
}
