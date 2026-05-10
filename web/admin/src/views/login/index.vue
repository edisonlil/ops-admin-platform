<template>
  <div class="view-account">
    <main class="view-account-shell animate__animated animate__fadeIn">
      <section class="view-account-brand" aria-labelledby="login-title">
        <div class="brand-mark">
          <img :src="brandLogoUrl" :alt="platformName" />
        </div>
        <div class="brand-copy">
          <div class="brand-kicker">{{ copy.loginTitle }}</div>
          <h1 id="login-title" class="view-account-title" :style="{ fontSize: `${heroPlatformNameFontSize}px` }">
            {{ platformName }}
          </h1>
          <p class="view-account-top-desc">{{ websiteConfig.loginDesc }}</p>
        </div>
      </section>

      <section class="view-account-form">
        <n-form
          ref="formRef"
          label-placement="top"
          size="large"
          :model="formInline"
          :rules="rules"
          class="login-form"
        >
          <n-form-item :label="copy.tenantLabel" path="tenant_key" class="login-form-item">
            <n-input
              v-model:value="formInline.tenant_key"
              :placeholder="copy.tenantPlaceholder"
              class="login-input"
            />
          </n-form-item>

          <n-form-item :label="copy.usernameLabel" path="username" class="login-form-item username-item">
            <n-input
              v-model:value="formInline.username"
              :placeholder="copy.usernamePlaceholder"
              class="login-input"
            />
          </n-form-item>

          <n-form-item :label="copy.passwordLabel" path="password" class="login-form-item">
            <n-input
              v-model:value="formInline.password"
              type="password"
              showPasswordOn="click"
              :placeholder="copy.passwordPlaceholder"
              class="login-input"
              @keyup.enter="handleSubmit"
            />
          </n-form-item>

          <n-form-item class="default-color remember-forgot">
            <div class="flex-between-wrapper">
              <n-checkbox v-model:checked="autoLogin">{{ copy.keepSignedIn }}</n-checkbox>
              <a href="javascript:" class="text-link">{{ copy.forgotPassword }}</a>
            </div>
          </n-form-item>

          <n-form-item class="submit-item">
            <n-button
              type="primary"
              @click="handleSubmit"
              size="large"
              :loading="loading"
              block
              class="login-button"
            >
              {{ copy.signIn }}
            </n-button>
          </n-form-item>

          <div class="login-divider"><span>{{ copy.otherMethods }}</span></div>

          <div class="view-account-other">
            <div class="social-login" aria-label="other login methods">
              <a href="javascript:" class="social-icon" aria-label="GitHub login">
                <n-icon size="22">
                  <LogoGithub />
                </n-icon>
              </a>
              <a href="javascript:" class="social-icon" aria-label="Facebook login">
                <n-icon size="22">
                  <LogoFacebook />
                </n-icon>
              </a>
              <a href="javascript:" class="social-icon" aria-label="Wechat login">
                <n-icon size="22">
                  <LogoWechat />
                </n-icon>
              </a>
            </div>
            <a href="javascript:" class="text-link register-link">{{ copy.register }}</a>
          </div>
        </n-form>
      </section>
    </main>
  </div>
</template>

<script lang="ts" setup>
  import { computed, reactive, ref, onMounted } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { useUserStore } from '@/store/modules/user';
  import { useMessage } from 'naive-ui';
  import { ResultEnum } from '@/enums/httpEnum';
  import { LogoGithub, LogoFacebook, LogoWechat } from '@vicons/ionicons5';
  import { PageEnum } from '@/enums/pageEnum';
  import { websiteConfig } from '@/config/website.config';
  import { useAppearanceStore } from '@/store/modules/appearance';

  interface FormState {
    tenant_key: string;
    username: string;
    password: string;
  }

  const copy = {
    loginTitle: '\u6b22\u8fce\u56de\u6765',
    tenantLabel: '\u79df\u6237\u6807\u8bc6',
    tenantPlaceholder: '\u8bf7\u8f93\u5165\u79df\u6237\u6807\u8bc6',
    usernameLabel: '\u7528\u6237\u540d',
    usernamePlaceholder: '\u8bf7\u8f93\u5165\u7528\u6237\u540d',
    passwordLabel: '\u5bc6\u7801',
    passwordPlaceholder: '\u8bf7\u8f93\u5165\u5bc6\u7801',
    keepSignedIn: '\u4fdd\u6301\u767b\u5f55',
    forgotPassword: '\u5fd8\u8bb0\u5bc6\u7801',
    signIn: '\u767b\u5f55',
    otherMethods: '\u5176\u5b83\u767b\u5f55\u65b9\u5f0f',
    register: '\u6ce8\u518c\u8d26\u53f7',
    loading: '\u767b\u5f55\u4e2d...',
    success: '\u767b\u5f55\u6210\u529f\uff0c\u5373\u5c06\u8fdb\u5165\u7cfb\u7edf',
    fail: '\u767b\u5f55\u5931\u8d25',
    incomplete: '\u8bf7\u586b\u5199\u5b8c\u6574\u767b\u5f55\u4fe1\u606f',
  };

  const formRef = ref();
  const message = useMessage();
  const loading = ref(false);
  const autoLogin = ref(true);
  const LOGIN_NAME = PageEnum.BASE_LOGIN_NAME;

  const formInline = reactive({
    tenant_key: 'platform',
    username: 'admin',
    password: 'edc3000',
    isCaptcha: true,
  });

  const rules = {
    tenant_key: { required: true, message: copy.tenantPlaceholder, trigger: 'blur' },
    username: { required: true, message: copy.usernamePlaceholder, trigger: 'blur' },
    password: { required: true, message: copy.passwordPlaceholder, trigger: 'blur' },
  };

  const userStore = useUserStore();
  const appearanceStore = useAppearanceStore();
  const platformName = computed(() => appearanceStore.displayPlatformName);
  const platformLogoUrl = computed(() => appearanceStore.displayPlatformLogoUrl);
  const platformNameFontSize = computed(() => appearanceStore.displayPlatformNameFontSize);
  const brandLogoUrl = computed(() => platformLogoUrl.value || websiteConfig.loginImage);
  const heroPlatformNameFontSize = computed(() => Math.max(42, Math.min(64, platformNameFontSize.value * 2.4)));

  const router = useRouter();
  const route = useRoute();

  onMounted(() => {
    appearanceStore.loadPlatformBranding().catch(() => undefined);
    setTimeout(() => {
      const usernameInput = document.querySelector('.username-item input');
      if (usernameInput) {
        (usernameInput as HTMLElement).focus();
      }
    }, 300);
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    formRef.value.validate(async (errors) => {
      if (!errors) {
        const { tenant_key, username, password } = formInline;
        message.loading(copy.loading);
        loading.value = true;

        const params: FormState = {
          tenant_key,
          username,
          password,
        };

        try {
          const { code, message: msg } = await userStore.login(params);
          message.destroyAll();
          if (code == ResultEnum.SUCCESS) {
            const toPath = decodeURIComponent((route.query?.redirect || '/') as string);
            message.success(copy.success);
            if (route.name === LOGIN_NAME) {
              router.replace('/');
            } else router.replace(toPath);
          } else {
            message.info(msg || copy.fail);
          }
        } finally {
          loading.value = false;
        }
      } else {
        message.error(copy.incomplete);
      }
    });
  };
</script>

<style lang="less" scoped>
  .view-account {
    min-height: 100vh;
    overflow: auto;
    background:
      linear-gradient(135deg, color-mix(in srgb, var(--app-primary-soft-bg) 48%, transparent), transparent 42%),
      var(--app-page-bg);
    color: var(--app-text-color);
  }

  .view-account-shell {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(360px, 430px);
    gap: clamp(32px, 6vw, 76px);
    align-items: center;
    width: min(100%, 1040px);
    min-height: 100vh;
    margin: 0 auto;
    padding: clamp(32px, 7vh, 72px) clamp(20px, 5vw, 56px);
  }

  .view-account-brand {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    max-width: 460px;
    transform: translateY(-18px);
  }

  .brand-mark {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 72px;
    height: 72px;
    margin-bottom: 24px;
    overflow: hidden;
    color: #fff;
    font-size: 30px;
    font-weight: 700;
    background: var(--app-primary-color);
    border-radius: var(--app-card-radius);
    box-shadow: var(--app-shadow-sm);

    img {
      width: 100%;
      height: 100%;
      object-fit: contain;
      padding: 10px;
      background: var(--app-surface-bg);
    }
  }

  .brand-kicker {
    max-width: 460px;
    margin-bottom: 12px;
    overflow: hidden;
    color: var(--app-primary-color);
    font-weight: 700;
    line-height: 1.2;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .view-account-title {
    margin: 0;
    color: var(--app-text-color);
    font-weight: 700;
    line-height: 1.12;
    letter-spacing: 0;
  }

  .view-account-top-desc {
    max-width: 420px;
    margin: 16px 0 0;
    color: var(--app-icon-color);
    font-size: var(--app-font-size-base);
    line-height: 1.7;
  }

  .view-account-form {
    padding: 28px;
    border: 1px solid var(--app-card-border-color);
    border-radius: var(--app-card-radius);
    background: var(--app-card-bg);
    box-shadow: var(--app-card-shadow);
  }

  .login-form {
    padding: 0;

    :deep(.n-form-item-label) {
      min-height: auto;
      padding-bottom: 8px;
      color: var(--app-text-color);
      font-size: var(--app-font-size-sm);
      font-weight: 600;
      line-height: 1.4;
    }

    :deep(.n-form-item-feedback-wrapper) {
      min-height: 20px;
    }

    :deep(.n-input) {
      border-radius: var(--app-card-radius);
      background: var(--app-surface-bg);
    }

    :deep(.n-input-wrapper) {
      min-height: 42px;
    }

    :deep(.n-checkbox .n-checkbox__label) {
      color: var(--app-icon-color);
      font-size: var(--app-font-size-sm);
    }
  }

  .login-form-item {
    margin-bottom: 8px;
  }

  .login-input {
    :deep(.n-input__input-el) {
      height: 42px;
    }
  }

  .remember-forgot {
    margin-bottom: 2px;
  }

  .flex-between-wrapper {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    gap: 16px;
  }

  .submit-item {
    margin-bottom: 0;
  }

  .login-button {
    height: 44px;
    border-radius: var(--app-card-radius);
    font-size: var(--app-font-size-base);
    font-weight: 600;
  }

  .login-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 8px 0 16px;
    color: var(--app-icon-color);
    font-size: var(--app-font-size-sm);

    &::before,
    &::after {
      content: '';
      flex: 1;
      height: 1px;
      background: var(--app-border-color);
    }
  }

  .view-account-other {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .social-login {
    display: flex;
    gap: 10px;
  }

  .social-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border: 1px solid var(--app-border-color);
    border-radius: var(--app-card-radius);
    background: var(--app-surface-bg);
    color: var(--app-icon-color);
    transition: background-color 0.2s, border-color 0.2s;

    &:hover {
      color: var(--app-primary-color);
      border-color: var(--app-primary-color);
      background: var(--app-primary-soft-bg);
    }
  }

  .register-link {
    white-space: nowrap;
  }

  .text-link {
    color: var(--app-primary-color);
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  @media (max-width: 860px) {
    .view-account-shell {
      grid-template-columns: 1fr;
      gap: 28px;
      min-height: auto;
    }

    .view-account-brand {
      align-items: center;
      max-width: none;
      text-align: center;
      transform: none;
    }

    .view-account-title {
      font-size: 30px;
    }
  }

  @media (max-width: 480px) {
    .view-account-shell {
      padding: 24px 16px 36px;
    }

    .view-account-form {
      padding: 16px;
    }

    .view-account-title {
      font-size: 21px;
    }

    .view-account-other,
    .flex-between-wrapper {
      align-items: flex-start;
      flex-direction: column;
      gap: 10px;
    }
  }
</style>
