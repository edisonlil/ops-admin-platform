<template>
  <div class="account-settings-page">
    <aside class="account-settings-nav" aria-label="个人设置导航">
      <button
        v-for="item in navItems"
        :key="item.key"
        type="button"
        class="account-settings-nav__item"
        :class="{ 'account-settings-nav__item--active': activeKey === item.key }"
        @click="activeKey = item.key"
      >
        <span class="account-settings-nav__title">{{ item.name }}</span>
        <span class="account-settings-nav__desc">{{ item.desc }}</span>
      </button>
    </aside>

    <main class="account-settings-content">
      <BasicSetting v-if="activeKey === 'basic'" />
      <SafetySetting v-else />
    </main>
  </div>
</template>

<script lang="ts" setup>
  import { ref } from 'vue';
  import BasicSetting from './BasicSetting.vue';
  import SafetySetting from './SafetySetting.vue';

  type SettingKey = 'basic' | 'security';

  const navItems: Array<{ key: SettingKey; name: string; desc: string }> = [
    {
      key: 'basic',
      name: '基本设置',
      desc: '个人资料 / 部门 / 角色',
    },
    {
      key: 'security',
      name: '安全设置',
      desc: '登录密码',
    },
  ];

  const activeKey = ref<SettingKey>('basic');
</script>

<style lang="less" scoped>
  .account-settings-page {
    display: grid;
    grid-template-columns: 256px minmax(0, 1fr);
    min-height: calc(100vh - 170px);
    overflow: hidden;
    background: var(--app-surface-bg, #ffffff);
    border: 1px solid var(--app-border-color);
    border-radius: var(--app-card-radius);
    box-shadow: var(--app-shadow-card);
  }

  .account-settings-nav {
    padding: 22px 16px;
    background: var(--app-surface-bg, #ffffff);
    border-right: 1px solid var(--app-border-color);
  }

  .account-settings-nav__item {
    display: flex;
    width: 100%;
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
    padding: 14px 18px;
    margin-bottom: 8px;
    color: var(--app-text-color);
    text-align: left;
    cursor: pointer;
    background: transparent;
    border: 0;
    border-radius: var(--app-control-radius);
    transition: background-color 0.2s ease, color 0.2s ease;
  }

  .account-settings-nav__item:hover {
    background: color-mix(in srgb, var(--app-primary-color) 4%, var(--app-surface-bg, #ffffff));
  }

  .account-settings-nav__item--active {
    color: var(--app-primary-color);
    background: var(--app-primary-color-suppl);
  }

  .account-settings-nav__title {
    font-size: var(--app-font-size-lg);
    font-weight: var(--app-font-weight-strong);
    line-height: 1.35;
  }

  .account-settings-nav__desc {
    color: var(--app-text-color-secondary);
    font-size: var(--app-font-size-sm);
    line-height: 1.45;
  }

  .account-settings-nav__item--active .account-settings-nav__desc {
    color: var(--app-primary-color);
  }

  .account-settings-content {
    min-width: 0;
    padding: 28px 32px 36px;
  }

  @media (max-width: 900px) {
    .account-settings-page {
      grid-template-columns: 1fr;
    }

    .account-settings-nav {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      padding: 14px;
      border-right: 0;
      border-bottom: 1px solid var(--app-border-color);
    }

    .account-settings-nav__item {
      margin-bottom: 0;
    }

    .account-settings-content {
      padding: 20px 16px 28px;
    }
  }
</style>
