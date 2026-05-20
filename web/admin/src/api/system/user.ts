import { Alova } from '@/utils/http/alova/index';

/**
 * @description: 获取用户信息
 */
export function getUserInfo() {
  return Alova.Get('/admin_info');
}

export interface ProfileUpdatePayload {
  full_name?: string;
  current_password?: string;
  new_password?: string;
}

export function getProfile() {
  return Alova.Get('/auth/profile');
}

export function updateProfile(payload: ProfileUpdatePayload) {
  return Alova.Put('/auth/profile', payload);
}

/**
 * @description: 用户登录
 */
export function login(params) {
  return Alova.Post(
    '/login',
    {
      params,
    }
  );
}

/**
 * @description: 用户修改密码
 */
export function changePassword(params, uid) {
  return Alova.Post(`/user/u${uid}/changepw`, { params });
}

/**
 * @description: 用户登出
 */
export function logout(params) {
  return Alova.Post('/login/logout', {
    params,
  });
}
