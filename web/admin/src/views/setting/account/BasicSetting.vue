<template>
  <n-grid cols="1 s:1 m:2 l:2 xl:2 2xl:2" responsive="screen" :x-gap="24" :y-gap="16">
    <n-grid-item>
      <n-form ref="profileFormRef" :model="profileForm" :rules="profileRules" label-placement="left" :label-width="96">
        <n-form-item label="用户名">
          <n-input :value="userInfo.username || '-'" disabled />
        </n-form-item>
        <n-form-item label="姓名" path="full_name">
          <n-input v-model:value="profileForm.full_name" clearable placeholder="请输入姓名" maxlength="120" show-count />
        </n-form-item>
        <n-form-item label="当前租户">
          <n-input :value="currentTenantName" disabled />
        </n-form-item>
        <n-form-item label="角色">
          <n-space>
            <n-tag v-for="role in roleTags" :key="role.value" size="small" type="info">
              {{ role.label }}
            </n-tag>
            <n-text v-if="!roleTags.length" depth="3">暂无角色</n-text>
          </n-space>
        </n-form-item>
        <n-space>
          <n-button type="primary" :loading="saving" @click="submitProfile">保存资料</n-button>
        </n-space>
      </n-form>
    </n-grid-item>

    <n-grid-item>
      <n-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-placement="left" :label-width="96">
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
    </n-grid-item>
  </n-grid>
</template>

<script lang="ts" setup>
  import { computed, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { FormInst, FormRules } from 'naive-ui';
  import { getProfile, updateProfile } from '@/api/system/user';
  import { useUserStore } from '@/store/modules/user';

  const message = useMessage();
  const userStore = useUserStore();
  const profileFormRef = ref<FormInst | null>(null);
  const passwordFormRef = ref<FormInst | null>(null);
  const saving = ref(false);
  const savingPassword = ref(false);

  const profileForm = reactive({
    full_name: '',
  });
  const passwordForm = reactive({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });

  const userInfo = computed(() => userStore.info || {});
  const currentTenantName = computed(() => {
    const tenant = userInfo.value.current_tenant || {};
    return String(tenant.name || tenant.tenant_key || tenant.key || '-');
  });
  const roleTags = computed(() =>
    (userInfo.value.roles || []).map((role: any) => ({
      label: String(role.label || role.name || role.value || role.key || ''),
      value: String(role.value || role.key || role.label || role.name || ''),
    })).filter((role) => role.value)
  );

  const profileRules: FormRules = {
    full_name: [{ required: true, message: '请输入姓名', trigger: ['blur', 'input'] }],
  };
  const passwordRules: FormRules = {
    current_password: [{ required: true, message: '请输入当前密码', trigger: ['blur', 'input'] }],
    new_password: [{ required: true, min: 6, message: '请输入至少 6 位新密码', trigger: ['blur', 'input'] }],
    confirm_password: [
      { required: true, message: '请再次输入新密码', trigger: ['blur', 'input'] },
      {
        validator: (_rule, value) => value === passwordForm.new_password,
        message: '两次输入的新密码不一致',
        trigger: ['blur', 'input'],
      },
    ],
  };

  async function refreshProfile() {
    const profile = await getProfile();
    userStore.setUserInfo(profile);
    profileForm.full_name = String(profile.full_name || '');
  }

  async function submitProfile() {
    try {
      await profileFormRef.value?.validate();
    } catch {
      return;
    }
    saving.value = true;
    try {
      const profile = await updateProfile({ full_name: profileForm.full_name.trim() });
      userStore.setUserInfo(profile);
      profileForm.full_name = String(profile.full_name || '');
      message.success('个人资料已保存');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '个人资料保存失败');
    } finally {
      saving.value = false;
    }
  }

  async function submitPassword() {
    try {
      await passwordFormRef.value?.validate();
    } catch {
      return;
    }
    savingPassword.value = true;
    try {
      const profile = await updateProfile({
        full_name: profileForm.full_name.trim(),
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

  refreshProfile();
</script>
