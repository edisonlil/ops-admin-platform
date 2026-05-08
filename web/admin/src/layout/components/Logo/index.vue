<template>
  <div class="logo" :class="{ 'logo--name-only': !showLogo }">
    <img
      v-if="showLogo"
      :src="platformLogoUrl"
      :alt="platformName"
      :class="{ 'mr-2': !collapsed }"
      @error="logoLoadFailed = true"
    />
    <h2 v-show="!collapsed || !showLogo" class="title" :style="{ fontSize: `${platformNameFontSize}px` }">
      {{ platformName }}
    </h2>
  </div>
</template>

<script lang="ts" setup>
  import { computed, ref, watch } from 'vue';
  import { useAppearanceStore } from '@/store/modules/appearance';

  defineOptions({
    name: 'Index',
  });

  defineProps({
    collapsed: {
      type: Boolean,
    },
  });

  const appearanceStore = useAppearanceStore();
  const logoLoadFailed = ref(false);
  const platformName = computed(() => appearanceStore.displayPlatformName);
  const platformLogoUrl = computed(() => appearanceStore.displayPlatformLogoUrl);
  const platformNameFontSize = computed(() => appearanceStore.displayPlatformNameFontSize);
  const showLogo = computed(() => !!platformLogoUrl.value && !logoLoadFailed.value);

  watch(platformLogoUrl, () => {
    logoLoadFailed.value = false;
  });
</script>

<style lang="less" scoped>
  .logo {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 64px;
    line-height: 64px;
    overflow: hidden;
    white-space: nowrap;

    img {
      width: auto;
      height: 32px;
      max-width: 42px;
      object-fit: contain;
    }

    .title {
      margin: 0;
      min-width: 0;
      overflow: hidden;
      color: inherit;
      font-size: 20px;
      font-weight: 650;
      line-height: 28px;
      text-overflow: ellipsis;
    }

    &--name-only {
      justify-content: flex-start;
      padding: 0 24px;
    }
  }
</style>
