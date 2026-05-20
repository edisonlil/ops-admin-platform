<template>
  <div class="profile-basic">
    <section class="profile-basic__main">
      <header class="profile-section-header">
        <span class="profile-section-header__eyebrow">个人基本信息</span>
        <h2>基本设置</h2>
        <p>维护当前账号的姓名，并查看该账号在当前租户下的部门与角色。</p>
      </header>

      <n-form
        ref="profileFormRef"
        :model="profileForm"
        :rules="profileRules"
        label-placement="top"
        class="profile-form"
      >
        <n-form-item label="姓名" path="full_name">
          <n-input v-model:value="profileForm.full_name" clearable placeholder="请输入姓名" maxlength="120" show-count />
        </n-form-item>
        <n-form-item label="用户名">
          <n-input :value="userInfo.username || '-'" disabled />
        </n-form-item>
        <n-form-item label="当前租户">
          <n-input :value="currentTenantName" disabled />
        </n-form-item>
        <n-space>
          <n-button type="primary" :loading="saving" @click="submitProfile">保存基本信息</n-button>
        </n-space>
      </n-form>

      <section class="profile-info-block">
        <div class="profile-info-block__head">
          <h3>所在部门</h3>
          <span>{{ departmentTags.length }} 个部门</span>
        </div>
        <div class="profile-tag-list">
          <n-tag
            v-for="department in departmentTags"
            :key="department.value"
            size="small"
            :type="department.primary ? 'success' : 'info'"
          >
            {{ department.label }}
            <template v-if="department.primary"> · 主部门</template>
          </n-tag>
          <n-text v-if="!departmentTags.length" depth="3">暂无部门</n-text>
        </div>
      </section>

      <section class="profile-info-block">
        <div class="profile-info-block__head">
          <h3>角色</h3>
          <span>{{ roleTags.length }} 个角色</span>
        </div>
        <div class="profile-tag-list">
          <n-tag v-for="role in roleTags" :key="role.value" size="small" type="info">
            {{ role.label }}
          </n-tag>
          <n-text v-if="!roleTags.length" depth="3">暂无角色</n-text>
        </div>
      </section>
    </section>

    <aside class="profile-basic__side" :class="{ 'profile-basic__side--compact': !avatarSrc }">
      <div v-if="avatarSrc" class="profile-avatar-panel">
        <n-avatar round :size="104" :src="avatarSrc">
          {{ avatarFallback }}
        </n-avatar>
        <h3>{{ displayName }}</h3>
        <p>{{ userInfo.username || '-' }}</p>
      </div>

      <dl class="profile-summary">
        <div>
          <dt>当前租户</dt>
          <dd>{{ currentTenantName }}</dd>
        </div>
        <div>
          <dt>主部门</dt>
          <dd>{{ primaryDepartmentName }}</dd>
        </div>
        <div>
          <dt>角色</dt>
          <dd>{{ roleSummary }}</dd>
        </div>
      </dl>
    </aside>
  </div>
</template>

<script lang="ts" setup>
  import { computed, reactive, ref } from 'vue';
  import { useMessage } from 'naive-ui';
  import type { FormInst, FormRules } from 'naive-ui';
  import { getProfile, updateProfile } from '@/api/system/user';
  import { useUserStore } from '@/store/modules/user';

  type TagItem = {
    label: string;
    value: string;
    primary?: boolean;
  };

  const message = useMessage();
  const userStore = useUserStore();
  const profileFormRef = ref<FormInst | null>(null);
  const saving = ref(false);

  const profileForm = reactive({
    full_name: '',
  });

  const userInfo = computed(() => userStore.info || {});
  const avatarSrc = computed(() => String(userInfo.value.avatar || '').trim());
  const displayName = computed(() => profileForm.full_name || userInfo.value.full_name || userInfo.value.username || '-');
  const avatarFallback = computed(() => String(displayName.value || userInfo.value.username || '用').slice(0, 1).toUpperCase());
  const currentTenantName = computed(() => {
    const tenant = userInfo.value.current_tenant || {};
    return String(tenant.name || tenant.tenant_key || tenant.key || '-');
  });

  const departmentTags = computed<TagItem[]>(() =>
    (userInfo.value.departments || [])
      .map((department: Recordable) => ({
        label: String(department.name || department.code || department.department_id || ''),
        value: String(department.department_id || department.id || department.code || department.name || ''),
        primary: Boolean(department.is_primary),
      }))
      .filter((department) => department.value)
  );
  const primaryDepartmentName = computed(() => {
    const primary = departmentTags.value.find((department) => department.primary) || departmentTags.value[0];
    return primary?.label || '暂无部门';
  });
  const roleTags = computed<TagItem[]>(() =>
    (userInfo.value.roles || [])
      .map((role: Recordable) => ({
        label: String(role.label || role.name || role.value || role.key || role.role_key || ''),
        value: String(role.value || role.key || role.role_key || role.label || role.name || ''),
      }))
      .filter((role) => role.value)
  );
  const roleSummary = computed(() => roleTags.value.map((role) => role.label).join('、') || '暂无角色');

  const profileRules: FormRules = {
    full_name: [{ required: true, message: '请输入姓名', trigger: ['blur', 'input'] }],
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
      message.success('基本信息已保存');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '基本信息保存失败');
    } finally {
      saving.value = false;
    }
  }

  refreshProfile();
</script>

<style lang="less" scoped>
  .profile-basic {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 300px;
    gap: 48px;
  }

  .profile-basic__main,
  .profile-basic__side {
    min-width: 0;
  }

  .profile-section-header {
    margin-bottom: 24px;
  }

  .profile-section-header__eyebrow {
    color: var(--app-primary-color);
    font-family: var(--app-font-family-mono);
    font-size: var(--app-font-size-sm);
    font-weight: var(--app-font-weight-strong);
  }

  .profile-section-header h2 {
    margin: 8px 0 8px;
    color: var(--app-text-color);
    font-size: 26px;
    font-weight: 700;
    line-height: 1.25;
  }

  .profile-section-header p {
    max-width: 560px;
    margin: 0;
    color: var(--app-text-color-secondary);
    font-size: var(--app-font-size-md);
    line-height: 1.7;
  }

  .profile-form {
    max-width: 520px;
  }

  .profile-info-block {
    max-width: 640px;
    padding-top: 24px;
    margin-top: 26px;
    border-top: 1px solid var(--app-border-color);
  }

  .profile-info-block__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 14px;
  }

  .profile-info-block__head h3 {
    margin: 0;
    color: var(--app-text-color);
    font-size: var(--app-font-size-lg);
    font-weight: var(--app-font-weight-strong);
  }

  .profile-info-block__head span {
    color: var(--app-text-color-secondary);
    font-size: var(--app-font-size-sm);
  }

  .profile-tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    min-height: 30px;
    align-items: center;
  }

  .profile-basic__side {
    padding-top: 82px;
  }

  .profile-basic__side--compact {
    padding-top: 64px;
  }

  .profile-avatar-panel {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 26px 20px;
    background: var(--app-surface-bg, #ffffff);
    border: 1px solid var(--app-border-color);
    border-radius: var(--app-card-radius);
  }

  .profile-avatar-panel h3 {
    margin: 16px 0 4px;
    color: var(--app-text-color);
    font-size: var(--app-font-size-lg);
    font-weight: var(--app-font-weight-strong);
  }

  .profile-avatar-panel p {
    margin: 0;
    color: var(--app-text-color-secondary);
    font-size: var(--app-font-size-sm);
  }

  .profile-summary {
    padding: 4px 0 0;
    margin: 18px 0 0;
  }

  .profile-summary div {
    display: grid;
    grid-template-columns: 76px minmax(0, 1fr);
    gap: 12px;
    padding: 14px 0;
    border-bottom: 1px solid var(--app-border-color);
  }

  .profile-summary dt,
  .profile-summary dd {
    margin: 0;
    font-size: var(--app-font-size-sm);
    line-height: 1.55;
  }

  .profile-summary dt {
    color: var(--app-text-color-secondary);
  }

  .profile-summary dd {
    color: var(--app-text-color);
    word-break: break-word;
  }

  @media (max-width: 1100px) {
    .profile-basic {
      grid-template-columns: 1fr;
      gap: 28px;
    }

    .profile-basic__side {
      padding-top: 0;
    }
  }
</style>
