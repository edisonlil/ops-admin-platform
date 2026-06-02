<template>
  <n-layout class="layout" :position="fixedMenu" has-sider>
    <n-layout-sider
      v-if="
        !isMobile && isMixMenuNoneSub && (navMode === 'vertical' || navMode === 'horizontal-mix')
      "
      show-trigger="bar"
      @collapse="collapsed = true"
      :position="fixedMenu"
      @expand="collapsed = false"
      :collapsed="collapsed"
      collapse-mode="width"
      :collapsed-width="appearanceStore.layoutConfig.collapsedMenuWidth"
      :width="leftMenuWidth"
      :native-scrollbar="false"
      :inverted="inverted"
      class="layout-sider"
    >
      <Logo :collapsed="collapsed" />
      <AsideMenu v-model:collapsed="collapsed" v-model:location="getMenuLocation" />
    </n-layout-sider>

    <n-drawer
      v-model:show="showSideDrawer"
      :width="appearanceStore.layoutConfig.menuWidth"
      :placement="'left'"
      class="layout-side-drawer"
    >
      <n-layout-sider
        :position="fixedMenu"
        :collapsed="false"
        :width="menuWidth"
        :native-scrollbar="false"
        :inverted="inverted"
        class="layout-sider"
      >
        <Logo :collapsed="collapsed" />
        <AsideMenu v-model:location="getMenuLocation" />
      </n-layout-sider>
    </n-drawer>

    <n-layout :inverted="inverted">
      <n-layout-header :inverted="getHeaderInverted" :position="fixedHeader">
        <PageHeader v-model:collapsed="collapsed" :inverted="inverted" />
      </n-layout-header>

      <n-layout-content
        class="layout-content"
        :class="{ 'layout-default-background': getDarkTheme === false }"
      >
        <div
          class="layout-content-main"
          :class="{
            'layout-content-main-fix': fixedMulti,
            'fluid-header': fixedHeader === 'static',
          }"
        >
          <TabsView v-if="isMultiTabs" v-model:collapsed="collapsed" />
          <div
            class="main-view"
            :class="{
              'main-view-fix': fixedMulti,
              noMultiTabs: !isMultiTabs,
              'mt-3': !isMultiTabs,
            }"
          >
            <MainView />
          </div>
        </div>
        <!--1.15废弃，没啥用，占用操作空间-->
        <!--        <NLayoutFooter v-if="getShowFooter">-->
        <!--          <PageFooter />-->
        <!--        </NLayoutFooter>-->
      </n-layout-content>
      <n-back-top :right="100" />
    </n-layout>
  </n-layout>
</template>

<script lang="ts" setup>
  import { ref, unref, computed, onMounted } from 'vue';
  import { Logo } from './components/Logo';
  import { TabsView } from './components/TagsView';
  import { MainView } from './components/Main';
  import { AsideMenu } from './components/Menu';
  import { PageHeader } from './components/Header';
  import { useProjectSetting } from '@/hooks/setting/useProjectSetting';
  import { useDesignSetting } from '@/hooks/setting/useDesignSetting';
  import { useRoute } from 'vue-router';
  import { useProjectSettingStore } from '@/store/modules/projectSetting';
  import { useAppearanceStore } from '@/store/modules/appearance';

  const { getDarkTheme } = useDesignSetting();
  const {
    // showFooter,
    navMode,
    navTheme,
    headerSetting,
    menuSetting,
    multiTabsSetting,
  } = useProjectSetting();

  const settingStore = useProjectSettingStore();
  const appearanceStore = useAppearanceStore();

  const collapsed = ref<boolean>(false);

  const { mobileWidth } = unref(menuSetting);

  const isMobile = computed<boolean>({
    get: () => settingStore.getIsMobile,
    set: (val) => settingStore.setIsMobile(val),
  });

  const fixedHeader = computed(() => {
    const { fixed } = unref(headerSetting);
    return fixed ? 'absolute' : 'static';
  });

  const isMixMenuNoneSub = computed(() => {
    const mixMenu = unref(menuSetting).mixMenu;
    const currentRoute = useRoute();
    if (unref(navMode) != 'horizontal-mix') return true;
    if (unref(navMode) === 'horizontal-mix' && mixMenu && currentRoute.meta.isRoot) {
      return false;
    }
    return true;
  });

  const fixedMenu = computed(() => {
    const { fixed } = unref(headerSetting);
    return fixed ? 'absolute' : 'static';
  });

  const isMultiTabs = computed(() => {
    return unref(multiTabsSetting).show;
  });

  const fixedMulti = computed(() => {
    return unref(multiTabsSetting).fixed;
  });

  const inverted = computed(() => {
    return ['dark', 'header-dark'].includes(unref(navTheme));
  });

  const getHeaderInverted = computed(() => {
    return ['light', 'header-dark'].includes(unref(navTheme)) ? unref(inverted) : !unref(inverted);
  });

  const leftMenuWidth = computed(() => {
    return collapsed.value
      ? appearanceStore.layoutConfig.collapsedMenuWidth
      : appearanceStore.layoutConfig.menuWidth;
  });

  const getMenuLocation = computed(() => {
    return 'left';
  });

  // 控制显示或隐藏移动端侧边栏
  const showSideDrawer = computed({
    get: () => isMobile.value && collapsed.value,
    set: (val) => (collapsed.value = val),
  });

  //判断是否触发移动端模式
  const checkMobileMode = () => {
    if (document.body.clientWidth <= mobileWidth) {
      isMobile.value = true;
    } else {
      isMobile.value = false;
    }
    collapsed.value = false;
  };

  const watchWidth = () => {
    const Width = document.body.clientWidth;
    if (Width <= 950) {
      collapsed.value = true;
    } else collapsed.value = false;

    checkMobileMode();
  };

  onMounted(() => {
    checkMobileMode();
    window.addEventListener('resize', watchWidth);
  });
</script>

<style lang="less">
  .layout-side-drawer {
    background-color: var(--app-menu-bg);

    .layout-sider {
      min-height: 100vh;
      box-shadow: var(--app-shadow-sm);
      position: relative;
      z-index: 13;
      transition: all 0.2s ease-in-out;
      background: var(--app-menu-bg);
    }
  }
</style>
<style lang="less" scoped>
  .layout {
    display: flex;
    flex-direction: row;
    flex: auto;

    &-default-background {
      background: var(--app-page-bg);
    }

    .layout-sider {
      min-height: 100vh;
      background: var(--app-menu-bg);
      box-shadow: var(--app-shadow-sm);
      position: relative;
      z-index: 13;
      transition: all 0.2s ease-in-out;

      :deep(.n-layout-sider-scroll-container) {
        background: var(--app-menu-bg);
      }

      :deep(.n-menu) {
        background: var(--app-menu-bg);
      }

      :deep(.n-menu .n-menu-item-content--selected),
      :deep(.n-menu .n-menu-item-content--child-active) {
        color: var(--app-menu-item-active-text-color-inverted);
        background-color: var(--app-menu-item-bg-active-inverted);
      }

      :deep(.n-menu .n-menu-item-content--selected .n-menu-item-content-header),
      :deep(.n-menu .n-menu-item-content--selected .n-menu-item-content__icon),
      :deep(.n-menu .n-menu-item-content--selected .n-menu-item-content__arrow),
      :deep(.n-menu .n-menu-item-content--child-active .n-menu-item-content-header),
      :deep(.n-menu .n-menu-item-content--child-active .n-menu-item-content__icon),
      :deep(.n-menu .n-menu-item-content--child-active .n-menu-item-content__arrow) {
        color: var(--app-menu-item-active-text-color-inverted);
      }
    }

    .layout-sider-fix {
      position: fixed;
      top: 0;
      left: 0;
    }

    .ant-layout {
      overflow: hidden;
    }

    .layout-right-fix {
      overflow-x: hidden;
      padding-left: 200px;
      min-height: 100vh;
      transition: all 0.2s ease-in-out;
    }

    .layout-content {
      flex: auto;
      min-height: 100vh;
    }

    .n-layout-header.n-layout-header--absolute-positioned {
      z-index: 11;
    }

    .n-layout-footer {
      background: none;
    }
  }

  .layout-content-main {
    margin: var(--app-content-margin);
    position: relative;
    padding-top: var(--app-header-height);
  }

  .layout-content-main-fix {
    padding-top: var(--app-header-height);
  }

  .fluid-header {
    padding-top: 0;
  }

  .main-view-fix {
    padding-top: var(--app-tabs-height);
  }

  .noMultiTabs {
    padding-top: 0;
  }
</style>
