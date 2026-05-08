<template>
  <NConfigProvider
    v-if="!isLock"
    :locale="zhCN"
    :theme="getDarkTheme"
    :theme-overrides="appearanceStore.themeOverrides"
    :date-locale="dateZhCN"
  >
    <div class="appearance-root" :class="appearanceStore.effectiveSkinClass" :style="appearanceStore.cssVars">
      <AppProvider>
        <RouterView />
      </AppProvider>
    </div>
  </NConfigProvider>

  <transition v-if="isLock && $route.name !== 'login'" name="slide-up">
    <LockScreen />
  </transition>
</template>

<script lang="ts" setup>
  import { computed, onMounted, onUnmounted, watch } from 'vue';
  import { zhCN, dateZhCN, darkTheme } from 'naive-ui';
  import { LockScreen } from '@/components/Lockscreen';
  import { AppProvider } from '@/components/Application';
  import { useScreenLockStore } from '@/store/modules/screenLock.js';
  import { useRoute } from 'vue-router';
  import { useDesignSettingStore } from '@/store/modules/designSetting';
  import { useAppearanceStore } from '@/store/modules/appearance';
  import { useUserStore } from '@/store/modules/user';

  const route = useRoute();
  const useScreenLock = useScreenLockStore();
  const designStore = useDesignSettingStore();
  const userStore = useUserStore();
  const appearanceStore = useAppearanceStore();
  const isLock = computed(() => useScreenLock.isLocked);
  const lockTime = computed(() => useScreenLock.lockTime);

  const getDarkTheme = computed(() => (designStore.darkTheme ? darkTheme : undefined));

  let timer: NodeJS.Timer;

  const syncAppearanceTheme = () => {
    appearanceStore.loadPlatformBranding().catch(() => undefined);
    if (route.name == 'login' || !userStore.getToken) {
      appearanceStore.ensureLoadedForCurrentTenant();
      return;
    }
    appearanceStore.loadEffectiveThemeForCurrentTenant().catch(() => appearanceStore.ensureLoadedForCurrentTenant());
  };

  const timekeeping = () => {
    clearInterval(timer);
    if (route.name == 'login' || isLock.value) return;
    // 设置不锁屏
    useScreenLock.setLock(false);
    // 重置锁屏时间
    useScreenLock.setLockTime();
    timer = setInterval(() => {
      // 锁屏倒计时递减
      useScreenLock.setLockTime(lockTime.value - 1);
      if (lockTime.value <= 0) {
        // 设置锁屏
        useScreenLock.setLock(true);
        return clearInterval(timer);
      }
    }, 1000);
  };

  onMounted(() => {
    syncAppearanceTheme();
    document.addEventListener('mousedown', timekeeping);
  });

  watch(
    () => [userStore.info?.current_tenant, userStore.info?.username, userStore.username],
    () => syncAppearanceTheme(),
    { deep: true }
  );

  onUnmounted(() => {
    document.removeEventListener('mousedown', timekeeping);
  });
</script>

<style lang="less">
  .appearance-root {
    min-height: 100vh;
    color: var(--app-text-color);
    background: var(--app-page-bg);
  }
</style>
