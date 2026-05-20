import { PageEnum } from '@/enums/pageEnum';
import { ErrorPageRoute } from '@/router/base';
import { useAsyncRoute } from '@/store/modules/asyncRoute';
import { useUser } from '@/store/modules/user';
import { ACCESS_TOKEN } from '@/store/mutation-types';
import { storage } from '@/utils/Storage';
import { useAppearanceStore } from '@/store/modules/appearance';
import { trackVisitorVisit } from '@/api/auditLogging';
import type { RouteRecordRaw } from 'vue-router';
import { isNavigationFailure, Router } from 'vue-router';
import { RedirectName } from './constant';

const LOGIN_PATH = PageEnum.BASE_LOGIN;

const whitePathList = [LOGIN_PATH]; // no redirect whitelist
const VISITOR_ID_KEY = 'ops-admin-visitor-id';
let lastTrackedPath = '';

export function createRouterGuards(router: Router) {
  const userStore = useUser();
  const asyncRouteStore = useAsyncRoute();
  router.beforeEach(async (to, from, next) => {
    const Loading = window['$loading'] || null;
    Loading && Loading.start();
    if (from.path === LOGIN_PATH && to.name === 'errorPage') {
      next(PageEnum.BASE_HOME);
      return;
    }

    // Whitelist can be directly entered
    if (whitePathList.includes(to.path as PageEnum)) {
      next();
      return;
    }

    const token = storage.get(ACCESS_TOKEN);

    if (!token) {
      // You can access without permissions. You need to set the routing meta.ignoreAuth to true
      if (to.meta.ignoreAuth) {
        next();
        return;
      }
      // redirect login page
      const redirectData: { path: string; replace: boolean; query?: Recordable<string> } = {
        path: LOGIN_PATH,
        replace: true,
      };
      if (to.path) {
        redirectData.query = {
          ...redirectData.query,
          redirect: to.path,
        };
      }
      next(redirectData);
      return;
    }

    if (asyncRouteStore.getIsDynamicRouteAdded) {
      next();
      return;
    }

    let routes: RouteRecordRaw[] = [];
    try {
      const userInfo = await userStore.getInfo();
      routes = await asyncRouteStore.generateRoutes(userInfo);
    } catch (error) {
      console.warn(error, '获取用户信息失败');
      await userStore.logout();
      next({
        path: LOGIN_PATH,
        replace: true,
        query: to.fullPath ? { redirect: to.fullPath } : undefined,
      });
      Loading && Loading.finish();
      return;
    }

    // 动态添加可访问路由表
    routes.forEach((item) => {
      router.addRoute(item as unknown as RouteRecordRaw);
    });

    //添加404
    const isErrorPage = router.getRoutes().findIndex((item) => item.name === ErrorPageRoute.name);
    if (isErrorPage === -1) {
      router.addRoute(ErrorPageRoute as unknown as RouteRecordRaw);
    }

    const redirectPath = (from.query.redirect || to.path) as string;
    const redirect = decodeURIComponent(redirectPath);
    const nextData = to.path === redirect ? { ...to, replace: true } : { path: redirect };
    asyncRouteStore.setDynamicRouteAdded(true);
    next(nextData);
    Loading && Loading.finish();
  });

  router.afterEach((to, _, failure) => {
    const appearanceStore = useAppearanceStore();
    document.title = appearanceStore.displayPlatformName;
    if (isNavigationFailure(failure)) {
      //console.log('failed navigation', failure)
    }
    const asyncRouteStore = useAsyncRoute();
    // 在这里设置需要缓存的组件名称
    const keepAliveComponents = asyncRouteStore.keepAliveComponents;
    const currentComName: any = to.matched.find((item) => item.name == to.name)?.name;
    if (currentComName && !keepAliveComponents.includes(currentComName) && to.meta?.keepAlive) {
      // 需要缓存的组件
      keepAliveComponents.push(currentComName);
    } else if (!to.meta?.keepAlive || to.name == RedirectName) {
      // 不需要缓存的组件
      const index = asyncRouteStore.keepAliveComponents.findIndex((name) => name == currentComName);
      if (index != -1) {
        keepAliveComponents.splice(index, 1);
      }
    }
    asyncRouteStore.setKeepAliveComponents(keepAliveComponents);
    trackVisitorRoute(to);
    const Loading = window['$loading'] || null;
    Loading && Loading.finish();
  });

  router.onError((error) => {
    console.log(error, '路由错误');
  });
}

function trackVisitorRoute(to: any) {
  const path = to.fullPath || to.path || '/';
  if (lastTrackedPath === path || shouldSkipVisitorTrack(path)) return;
  lastTrackedPath = path;
  trackVisitorVisit({
    path,
    title: String(to.meta?.title || document.title || ''),
    referrer: document.referrer || '',
    visitor_id: ensureVisitorId(),
    session_id: sessionStorage.getItem('ops-admin-session-id') || ensureSessionId(),
    device_type: resolveDeviceType(),
    browser: resolveBrowserName(),
    os: resolveOperatingSystem(),
  }).send().catch(() => undefined);
}

function shouldSkipVisitorTrack(path: string) {
  return path.startsWith('/audit/') || path.startsWith('/login') || path.startsWith('/redirect');
}

function ensureVisitorId() {
  const existing = localStorage.getItem(VISITOR_ID_KEY);
  if (existing) return existing;
  const value = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
  localStorage.setItem(VISITOR_ID_KEY, value);
  return value;
}

function ensureSessionId() {
  const key = 'ops-admin-session-id';
  const existing = sessionStorage.getItem(key);
  if (existing) return existing;
  const value = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
  sessionStorage.setItem(key, value);
  return value;
}

function resolveDeviceType() {
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes('mobile') || ua.includes('android') || ua.includes('iphone')) return 'mobile';
  if (ua.includes('ipad') || ua.includes('tablet')) return 'tablet';
  return 'desktop';
}

function resolveBrowserName() {
  const ua = navigator.userAgent;
  const edge = ua.match(/Edg\/([\d.]+)/);
  if (edge) return `Edge ${edge[1]}`.slice(0, 80);
  const chrome = ua.match(/Chrome\/([\d.]+)/);
  if (chrome) return `Chrome ${chrome[1]}`.slice(0, 80);
  const firefox = ua.match(/Firefox\/([\d.]+)/);
  if (firefox) return `Firefox ${firefox[1]}`.slice(0, 80);
  const safari = ua.match(/Version\/([\d.]+).*Safari/);
  if (safari) return `Safari ${safari[1]}`.slice(0, 80);
  return 'Unknown';
}

function resolveOperatingSystem() {
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes('windows')) return 'Windows';
  if (ua.includes('mac os')) return 'macOS';
  if (ua.includes('android')) return 'Android';
  if (ua.includes('iphone') || ua.includes('ipad')) return 'iOS';
  if (ua.includes('linux')) return 'Linux';
  return (navigator.platform || 'Unknown').slice(0, 80);
}
