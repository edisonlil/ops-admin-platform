import './styles/tailwind.css';
import './styles/index.less';
import { createApp } from 'vue';
import { setupNaiveDiscreteApi, setupNaive, setupDirectives } from '@/plugins';
import App from './App.vue';
import router, { setupRouter } from './router';
import { setupStore } from '@/store';
import { setupStarterModules } from './modules';
import { useAppearanceStore } from '@/store/modules/appearance';
import { useUserStore } from '@/store/modules/user';
import { PageEnum } from '@/enums/pageEnum';

async function bootstrap() {
  setupStarterModules();

  const app = createApp(App);

  // 挂载状态管理
  setupStore(app);

  const appearanceStore = useAppearanceStore();
  const userStore = useUserStore();
  const initialPath = window.location.pathname;
  if (initialPath === PageEnum.BASE_LOGIN || !userStore.getToken) {
    await Promise.all([
      appearanceStore.loadPlatformBranding().catch(() => undefined),
      appearanceStore.loadPlatformTheme().catch(() => appearanceStore.ensurePlatformThemeLoaded()),
    ]);
  } else {
    await Promise.all([
      appearanceStore.loadPlatformBranding().catch(() => undefined),
      appearanceStore
        .loadEffectiveThemeForCurrentTenant()
        .catch(() => appearanceStore.ensureLoadedForCurrentTenant()),
    ]);
  }

  // 注册全局常用的 naive-ui 组件
  setupNaive(app);

  // 挂载 naive-ui 脱离上下文的 Api
  setupNaiveDiscreteApi();

  // 注册全局自定义组件
  //setupCustomComponents();

  // 注册全局自定义指令，如：v-permission权限指令
  setupDirectives(app);

  // 注册全局方法，如：app.config.globalProperties.$message = message
  //setupGlobalMethods(app);

  // 挂载路由
  setupRouter(app);

  // 路由准备就绪后挂载 APP 实例
  // https://router.vuejs.org/api/interfaces/router.html#isready
  await router.isReady();

  // https://www.naiveui.com/en-US/os-theme/docs/style-conflict#About-Tailwind's-Preflight-Style-Override
  const meta = document.createElement('meta');
  meta.name = 'naive-ui-style';
  document.head.appendChild(meta);

  app.mount('#app', true);
}

void bootstrap();
