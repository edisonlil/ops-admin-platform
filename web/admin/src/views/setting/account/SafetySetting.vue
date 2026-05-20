<template>
  <div class="security-setting">
    <section class="security-setting__main">
      <header class="security-section-header">
        <span class="security-section-header__eyebrow">账号安全</span>
        <h2>安全设置</h2>
        <p>修改当前账号的登录密码。密码修改成功后，下次登录请使用新密码。</p>
      </header>

      <n-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-placement="top"
        class="security-form"
      >
        <n-form-item label="当前密码" path="current_password">
          <n-input v-model:value="passwordForm.current_password" type="password" show-password-on="mousedown" />
        </n-form-item>
        <n-form-item label="新密码" path="new_password">
          <n-input v-model:value="passwordForm.new_password" type="password" show-password-on="mousedown" />
        </n-form-item>
        <n-form-item label="确认密码" path="confirm_password">
          <n-input v-model:value="passwordForm.confirm_password" type="password" show-password-on="mousedown" />
        </n-form-item>
        <n-space>
          <n-button type="primary" secondary :loading="savingPassword" @click="submitPassword">修改密码</n-button>
        </n-space>
      </n-form>
    </section>

    <aside class="security-setting__tips">
      <h3>密码要求</h3>
      <ul>
        <li>至少 6 个字符。</li>
        <li>请避免与用户名或常用弱密码相同。</li>
        <li>修改后请妥善保管新密码。</li>
      </ul>
    </aside>
  </div>
</template>

<script lang="ts" setup>
  import { reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { FormInst, FormRules } from 'naive-ui';
  import { updateProfile } from '@/api/system/user';
  import { useUserStore } from '@/store/modules/user';

  const message = useMessage();
  const userStore = useUserStore();
  const passwordFormRef = ref<FormInst | null>(null);
  const savingPassword = ref(false);

  const passwordForm = reactive({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });

  const passwordRules: FormRules = {
    current_password: [{ required: true, message: '请输入当前密码', trigger: ['blur', 'input'] }],
    new_password: [{ required: true, min: 6, message: '请输入至少 6 个字符的新密码', trigger: ['blur', 'input'] }],
    confirm_password: [
      { required: true, message: '请再次输入新密码', trigger: ['blur', 'input'] },
      {
        validator: (_rule, value) => value === passwordForm.new_password,
        message: '两次输入的新密码不一致',
        trigger: ['blur', 'input'],
      },
    ],
  };

  async function submitPassword() {
    try {
      await passwordFormRef.value?.validate();
    } catch {
      return;
    }
    savingPassword.value = true;
    try {
      const profile = await updateProfile({
        full_name: String(userStore.info?.full_name || '').trim(),
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      userStore.setUserInfo(profile);
      Object.assign(passwordForm, { current_password: '', new_password: '', confirm_password: '' });
      passwordFormRef.value?.restoreValidation();
      message.success('密码已修改');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '密码修改失败');
    } finally {
      savingPassword.value = false;
    }
  }
</script>

<style lang="less" scoped>
  .security-setting {
    display: grid;
    grid-template-columns: minmax(0, 520px) minmax(240px, 300px);
    gap: 48px;
  }

  .security-section-header {
    margin-bottom: 24px;
  }

  .security-section-header__eyebrow {
    color: var(--app-primary-color);
    font-family: var(--app-font-family-mono);
    font-size: var(--app-font-size-sm);
    font-weight: var(--app-font-weight-strong);
  }

  .security-section-header h2 {
    margin: 8px 0 8px;
    color: var(--app-text-color);
    font-size: 26px;
    font-weight: 700;
    line-height: 1.25;
  }

  .security-section-header p {
    margin: 0;
    color: var(--app-text-color-secondary);
    font-size: var(--app-font-size-md);
    line-height: 1.7;
  }

  .security-form {
    max-width: 520px;
  }

  .security-setting__tips {
    align-self: start;
    padding: 22px;
    margin-top: 72px;
    background: var(--app-surface-bg, #ffffff);
    border: 1px solid var(--app-border-color);
    border-radius: var(--app-card-radius);
  }

  .security-setting__tips h3 {
    margin: 0 0 14px;
    color: var(--app-text-color);
    font-size: var(--app-font-size-lg);
    font-weight: var(--app-font-weight-strong);
  }

  .security-setting__tips ul {
    padding-left: 18px;
    margin: 0;
    color: var(--app-text-color-secondary);
    font-size: var(--app-font-size-sm);
    line-height: 1.8;
  }

  @media (max-width: 900px) {
    .security-setting {
      grid-template-columns: 1fr;
      gap: 28px;
    }

    .security-setting__tips {
      margin-top: 0;
    }
  }
</style>
