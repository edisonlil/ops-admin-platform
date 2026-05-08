import { defineStore } from 'pinia';
import { store } from '@/store';
import { ACCESS_TOKEN, CURRENT_USER, IS_SCREENLOCKED } from '@/store/mutation-types';
import { ResultEnum } from '@/enums/httpEnum';

import { getUserInfo as getUserInfoApi, login } from '@/api/system/user';
import { switchTenant as switchTenantApi } from '@/api/business';
import { storage } from '@/utils/Storage';
import { useAsyncRoute } from '@/store/modules/asyncRoute';
import { TABS_ROUTES } from '@/store/mutation-types';

export type UserInfoType = {
  username?: string;
  email?: string;
  current_tenant?: Recordable;
  tenant_memberships?: Recordable[];
  is_platform_admin?: boolean;
  permissions?: Recordable[];
  menus?: Recordable[];
};

export interface IUserState {
  token: string;
  username: string;
  welcome: string;
  avatar: string;
  permissions: any[];
  info: UserInfoType;
}

export const useUserStore = defineStore({
  id: 'app-user',
  state: (): IUserState => ({
    token: storage.get(ACCESS_TOKEN, ''),
    username: '',
    welcome: '',
    avatar: '',
    permissions: [],
    info: storage.get(CURRENT_USER, {}),
  }),
  getters: {
    getToken(): string {
      return this.token;
    },
    getAvatar(): string {
      return this.avatar;
    },
    getNickname(): string {
      return this.username;
    },
    getPermissions(): [any][] {
      return this.permissions;
    },
    getUserInfo(): UserInfoType {
      return this.info;
    },
  },
  actions: {
    resetRouteState() {
      const asyncRouteStore = useAsyncRoute();
      asyncRouteStore.setDynamicRouteAdded(false);
      asyncRouteStore.setRouters([]);
      asyncRouteStore.setMenus([]);
      localStorage.removeItem(TABS_ROUTES);
    },
    setToken(token: string) {
      this.token = token;
    },
    setAvatar(avatar: string) {
      this.avatar = avatar;
    },
    setPermissions(permissions) {
      this.permissions = permissions;
    },
    setUserInfo(info: UserInfoType) {
      this.info = info;
      this.username = info?.username ?? this.username;
    },
    // 登录
    async login(params: any) {
      const result = await login(params);
      if (result?.token) {
        const ex = 7 * 24 * 60 * 60;
        this.resetRouteState();
        storage.set(ACCESS_TOKEN, result.token, ex);
        storage.set(CURRENT_USER, result, ex);
        storage.set(IS_SCREENLOCKED, false);
        this.setToken(result.token);
        this.setUserInfo(result);
        this.username = result.username ?? this.username;
      }
      return { code: ResultEnum.SUCCESS, message: 'success', result };
    },

    // 获取用户信息
    async getInfo() {
      const result = await getUserInfoApi();
      if (result.permissions && result.permissions.length) {
        const permissionsList = result.permissions;
        this.setPermissions(permissionsList);
        this.setUserInfo(result);
      } else {
        throw new Error('getInfo: permissionsList must be a non-null array !');
      }
      this.username = result.username ?? this.username;
      this.setAvatar(result.avatar);
      return result;
    },
    async switchTenant(tenantId: number) {
      const result = await switchTenantApi(tenantId);
      const token = result?.token || result?.access_token;
      if (token) {
        const ex = 7 * 24 * 60 * 60;
        this.resetRouteState();
        storage.set(ACCESS_TOKEN, token, ex);
        storage.set(CURRENT_USER, result, ex);
        this.setToken(token);
      }
      this.setUserInfo(result);
      return result;
    },

    // 登出
    async logout() {
      this.setPermissions([]);
      this.setUserInfo({ username: '', email: '' });
      this.username = '';
      this.resetRouteState();
      storage.remove(ACCESS_TOKEN);
      storage.remove(CURRENT_USER);
    },
  },
});

// Need to be used outside the setup
export function useUser() {
  return useUserStore(store);
}
