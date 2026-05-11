<template>
  <div class="layout-header">
    <!--顶部菜单-->
    <div
      class="layout-header-left"
      v-if="navMode === 'horizontal' || (navMode === 'horizontal-mix' && mixMenu)"
    >
      <Logo v-if="navMode === 'horizontal'" class="header-logo" :collapsed="collapsed" />
      <AsideMenu
        :collapsed="collapsed"
        v-model:location="getMenuLocation"
        :inverted="getInverted"
        mode="horizontal"
      />
    </div>
    <!--左侧菜单-->
    <div class="layout-header-left" v-else>
      <!-- 菜单收起 -->
      <div
        class="ml-1 layout-header-trigger layout-header-trigger-min"
        @click="handleMenuCollapsed"
      >
        <n-icon size="18" v-if="collapsed">
          <MenuUnfoldOutlined />
        </n-icon>
        <n-icon size="18" v-else>
          <MenuFoldOutlined />
        </n-icon>
      </div>
      <!-- 刷新 -->
      <div
        class="mr-1 layout-header-trigger layout-header-trigger-min"
        v-if="headerSetting.isReload"
        @click="reloadPage"
      >
        <n-icon size="18">
          <ReloadOutlined />
        </n-icon>
      </div>
      <!-- 面包屑 -->
      <n-breadcrumb v-if="crumbsSetting.show">
        <template
          v-for="routeItem in breadcrumbList"
          :key="routeItem.name === RedirectName ? void 0 : routeItem.name"
        >
          <n-breadcrumb-item v-if="routeItem.meta.title">
            <n-dropdown
              v-if="routeItem.children.length"
              :options="routeItem.children"
              @select="dropdownSelect"
            >
              <span class="link-text">
                <component
                  v-if="crumbsSetting.showIcon && routeItem.meta.icon"
                  :is="routeItem.meta.icon"
                />
                {{ routeItem.meta.title }}
              </span>
            </n-dropdown>
            <span class="link-text" v-else>
              <component
                v-if="crumbsSetting.showIcon && routeItem.meta.icon"
                :is="routeItem.meta.icon"
              />
              {{ routeItem.meta.title }}
            </span>
          </n-breadcrumb-item>
        </template>
      </n-breadcrumb>
    </div>
    <div class="layout-header-right">
      <div
        class="layout-header-trigger layout-header-trigger-min"
        v-for="item in iconList"
        :key="item.icon"
      >
        <n-tooltip placement="bottom">
          <template #trigger>
            <n-icon size="18">
              <component :is="item.icon" v-on="item.eventObject || {}" />
            </n-icon>
          </template>
          <span>{{ item.tips }}</span>
        </n-tooltip>
      </div>
      <!--切换全屏-->
      <div class="layout-header-trigger layout-header-trigger-min">
        <n-tooltip placement="bottom">
          <template #trigger>
            <n-icon size="18">
              <component :is="fullscreenIcon" @click="toggleFullScreen" />
            </n-icon>
          </template>
          <span>全屏</span>
        </n-tooltip>
      </div>
      <div class="tenant-switcher" v-if="currentTenantName">
        <n-dropdown
          v-if="tenantOptions.length > 1 || isPlatformAdmin"
          trigger="click"
          :options="tenantOptions"
          @select="tenantSelect"
        >
          <div class="tenant-pill">
            <n-icon size="16">
              <ApartmentOutlined />
            </n-icon>
            <span>{{ currentTenantName }}</span>
          </div>
        </n-dropdown>
        <div class="tenant-pill" v-else>
          <n-icon size="16">
            <ApartmentOutlined />
          </n-icon>
          <span>{{ currentTenantName }}</span>
        </div>
      </div>
      <!-- 个人中心 -->
      <div class="layout-header-trigger layout-header-trigger-min message-entry" @click="openInbox">
        <n-tooltip placement="bottom">
          <template #trigger>
            <n-badge class="message-badge" :value="unreadCount" :max="99" :show="unreadCount > 0">
              <n-icon size="18">
                <BellOutlined />
              </n-icon>
            </n-badge>
          </template>
          <span>站内信</span>
        </n-tooltip>
      </div>
      <div class="layout-header-trigger layout-header-trigger-min">
        <n-dropdown trigger="hover" @select="avatarSelect" :options="avatarOptions">
          <div class="avatar">
            <span>{{ username }}</span>
          </div>
        </n-dropdown>
      </div>
      <!--设置-->
    </div>
  </div>
  <!--项目配置-->
</template>

<script lang="ts">
  import { useProjectSetting } from '@/hooks/setting/useProjectSetting';
  import { Logo } from '@/layout/components/Logo';
  import { AsideMenu } from '@/layout/components/Menu';
  import { RedirectName } from '@/router/constant';
  import { useDesignSettingStore } from '@/store/modules/designSetting';
  import { useScreenLockStore } from '@/store/modules/screenLock';
  import { useUserStore } from '@/store/modules/user';
  import { TABS_ROUTES } from '@/store/mutation-types';
  import { NDialogProvider, useDialog, useMessage } from 'naive-ui';
  import { computed, defineComponent, reactive, toRefs, unref } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { getMessagingUnreadCount } from '@/api/messaging';
  import components from './components';

  export default defineComponent({
    name: 'PageHeader',
    components: { ...components, NDialogProvider, AsideMenu, Logo },
    props: {
      collapsed: {
        type: Boolean,
      },
      inverted: {
        type: Boolean,
      },
    },
    emits: ['update:collapsed'],
    setup(props, { emit }) {
      const userStore = useUserStore();
      const designStore = useDesignSettingStore();
      const useLockscreen = useScreenLockStore();
      const message = useMessage();
      const dialog = useDialog();
      const { navMode, navTheme, headerSetting, menuSetting, crumbsSetting } = useProjectSetting();

      const state = reactive({
        username: userStore?.info?.username ?? '',
        unreadCount: 0,
        fullscreenIcon: 'FullscreenOutlined',
        navMode,
        navTheme,
        headerSetting,
        crumbsSetting,
      });

      const currentTenantName = computed(() => {
        const tenant = userStore.info?.current_tenant || {};
        return String(tenant.name || tenant.tenant_key || tenant.key || '');
      });

      const isPlatformAdmin = computed(() => !!userStore.info?.is_platform_admin);

      const tenantOptions = computed(() => {
        const memberships = userStore.info?.tenant_memberships || [];
        return memberships.map((tenant: any) => ({
          label: `${tenant.name || tenant.tenant_key || tenant.key}${tenant.status === 'suspended' ? ' (停用)' : ''}`,
          key: Number(tenant.id),
          disabled: tenant.status === 'suspended',
        }));
      });

      const getInverted = computed(() => {
        return ['light', 'header-dark'].includes(unref(navTheme))
          ? props.inverted
          : !props.inverted;
      });

      const mixMenu = computed(() => {
        return unref(menuSetting).mixMenu;
      });

      const getChangeStyle = computed(() => {
        const { collapsed } = props;
        const { minMenuWidth, menuWidth } = unref(menuSetting);
        return {
          left: collapsed ? `${minMenuWidth}px` : `${menuWidth}px`,
          width: `calc(100% - ${collapsed ? `${minMenuWidth}px` : `${menuWidth}px`})`,
        };
      });

      const getMenuLocation = computed(() => {
        return 'header';
      });

      const router = useRouter();
      const route = useRoute();

      const generator: any = (routerMap) => {
        return routerMap.map((item) => {
          const currentMenu = {
            ...item,
            label: item.meta.title,
            key: item.name,
            disabled: item.path === '/',
          };
          // 是否有子菜单，并递归处理
          if (item.children && item.children.length > 0) {
            // Recursion
            currentMenu.children = generator(item.children, currentMenu);
          }
          return currentMenu;
        });
      };

      const breadcrumbList = computed(() => {
        return generator(route.matched);
      });

      const dropdownSelect = (key) => {
        router.push({ name: key });
      };

      // 刷新页面
      const reloadPage = () => {
        router.push({
          path: '/redirect' + unref(route).fullPath,
        });
      };

      // 退出登录
      const doLogout = () => {
        dialog.info({
          title: '提示',
          content: '您确定要退出登录吗',
          positiveText: '确定',
          negativeText: '取消',
          onPositiveClick: () => {
            userStore.logout().then(() => {
              message.success('成功退出登录');
              // 移除标签页
              localStorage.removeItem(TABS_ROUTES);
              router
                .replace({
                  name: 'Login',
                  query: {
                    redirect: route.fullPath,
                  },
                })
                .finally(() => location.reload());
            });
          },
          onNegativeClick: () => {},
        });
      };

      // 切换全屏图标
      const toggleFullscreenIcon = () =>
        (state.fullscreenIcon =
          document.fullscreenElement !== null ? 'FullscreenExitOutlined' : 'FullscreenOutlined');

      // 监听全屏切换事件
      document.addEventListener('fullscreenchange', toggleFullscreenIcon);

      // 全屏切换
      const toggleFullScreen = () => {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen();
        } else {
          if (document.exitFullscreen) {
            document.exitFullscreen();
          }
        }
      };

      const toggleDarkTheme = () => {
        designStore.darkTheme = !designStore.darkTheme;
      };

      // 图标列表
      const iconList = computed(() => {
        return [
          {
            icon: designStore.darkTheme ? 'SunnySharp' : 'Moon',
            tips: designStore.darkTheme ? '切换亮色主题' : '切换暗色主题',
            eventObject: {
              click: toggleDarkTheme,
            },
          },
          {
            icon: 'SearchOutlined',
            tips: '搜索',
          },
          {
            icon: 'LockOutlined',
            tips: '锁屏',
            eventObject: {
              click: () => useLockscreen.setLock(true),
            },
          },
        ];
      });
      const avatarOptions = [
        {
          label: '个人设置',
          key: 1,
        },
        {
          label: '退出登录',
          key: 2,
        },
      ];

      //头像下拉菜单
      const avatarSelect = (key) => {
        switch (key) {
          case 1:
            router.push({ name: 'Setting' });
            break;
          case 2:
            doLogout();
            break;
        }
      };

      const tenantSelect = async (key) => {
        const tenantId = Number(key);
        if (!tenantId || tenantId === Number(userStore.info?.current_tenant?.id)) {
          return;
        }
        await userStore.switchTenant(tenantId);
        message.success('租户已切换');
        router.replace({ path: '/' }).finally(() => location.reload());
      };

      const loadUnreadCount = async () => {
        if (!userStore.getToken) return;
        try {
          const payload = await getMessagingUnreadCount();
          state.unreadCount = Number(payload?.count || 0);
        } catch {
          state.unreadCount = 0;
        }
      };

      const openInbox = () => {
        router.push({ name: 'message-inbox' });
      };

      loadUnreadCount();

      function handleMenuCollapsed() {
        emit('update:collapsed', !props.collapsed);
      }

      return {
        ...toRefs(state),
        iconList,
        toggleFullScreen,
        doLogout,
        route,
        dropdownSelect,
        avatarOptions,
        tenantOptions,
        currentTenantName,
        isPlatformAdmin,
        tenantSelect,
        openInbox,
        getChangeStyle,
        avatarSelect,
        breadcrumbList,
        reloadPage,
        getInverted,
        getMenuLocation,
        mixMenu,
        handleMenuCollapsed,
        RedirectName,
      };
    },
  });
</script>

<style lang="less" scoped>
  .layout-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0;
    height: 64px;
    height: var(--app-header-height);
    box-shadow: var(--app-shadow-sm);
    transition: all 0.2s ease-in-out;
    width: 100%;
    z-index: 11;

    &-left {
      display: flex;
      align-items: center;

      .header-logo {
        flex: 0 0 auto;
        max-width: 260px;
        min-width: 0;
        padding: 0 18px 0 0;
      }

      .logo {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 64px;
        height: var(--app-header-height);
        line-height: var(--app-header-height);
        overflow: hidden;
        white-space: nowrap;
        padding-left: 10px;

        img {
          width: auto;
          height: 32px;
          margin-right: 10px;
        }

        .title {
          margin-bottom: 0;
        }
      }

      ::v-deep(.ant-breadcrumb span:last-child .link-text) {
        color: #515a6e;
      }

      .n-breadcrumb {
        display: inline-block;
      }

      &-menu {
        color: var(--text-color);
      }
    }

    &-right {
      display: flex;
      align-items: center;
      margin-right: 20px;

      .avatar {
        display: flex;
        align-items: center;
        height: 64px;
        height: var(--app-header-height);
      }

      .tenant-switcher {
        display: flex;
        align-items: center;
        height: var(--app-header-height);
        padding: 0 8px;
      }

      .tenant-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        max-width: 220px;
        height: 30px;
        padding: 0 10px;
        border: 1px solid var(--app-border-color);
        border-radius: var(--app-card-radius);
        color: var(--app-icon-color);
        background: var(--app-surface-muted-bg);
        font-size: 13px;
        line-height: 30px;
        white-space: nowrap;
        overflow: hidden;

        span {
          overflow: hidden;
          text-overflow: ellipsis;
        }
      }

      .message-entry {
        display: inline-flex;
        align-items: center;

        :deep(.message-badge) {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 32px;
          height: 32px;
        }

        :deep(.n-icon) {
          align-items: center;
          justify-content: center;
          height: 32px;
          line-height: 32px;
        }

        :deep(.n-badge-sup) {
          top: 4px;
          right: 4px;
          min-width: 16px;
          height: 16px;
          padding: 0 5px;
          line-height: 16px;
        }
      }

      > * {
        cursor: pointer;
      }
    }

    &-trigger {
      display: inline-block;
      width: 64px;
      height: 64px;
      height: var(--app-header-height);
      text-align: center;
      cursor: pointer;
      transition: all 0.2s ease-in-out;

      .n-icon {
        display: flex;
        align-items: center;
        height: 64px;
        height: var(--app-header-height);
        line-height: var(--app-header-height);
      }

      &:hover {
        background: hsla(0, 0%, 100%, 0.08);
      }

      .anticon {
        font-size: 16px;
        color: #515a6e;
      }
    }

    &-trigger-min {
      width: auto;
      padding: 0 12px;
    }
  }

  .layout-header-light {
    background: #fff;
    color: #515a6e;

    .n-icon {
      color: #515a6e;
    }

    .layout-header-left {
      ::v-deep(.n-breadcrumb .n-breadcrumb-item:last-child .n-breadcrumb-item__link) {
        color: #515a6e;
      }
    }

    .layout-header-trigger {
      &:hover {
        background: var(--app-icon-hover-bg);
      }
    }
  }

  .layout-header-fix {
    position: fixed;
    top: 0;
    right: 0;
    left: var(--app-menu-width);
    z-index: 11;
  }

  //::v-deep(.menu-router-link) {
  //  color: #515a6e;
  //
  //  &:hover {
  //    color: #1890ff;
  //  }
  //}
</style>
