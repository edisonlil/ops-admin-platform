import { RouteRecordRaw } from 'vue-router';
import { Layout } from '@/router/constant';
import { RobotOutlined } from '@vicons/antd';
import { renderIcon } from '@/utils/index';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/ai',
    name: 'ai',
    redirect: '/ai/studio',
    component: Layout,
    meta: {
      title: 'AI Studio',
      icon: renderIcon(RobotOutlined),
      permissions: ['ai_studio:access'],
      sort: 84,
    },
    children: [
      {
        path: 'studio',
        name: 'ai-studio',
        meta: {
          title: 'AI Studio',
          permissions: ['ai_studio:access'],
        },
        component: () => import('@/views/ai/studio/index.vue'),
      },
      {
        path: 'studio/apps/:appKey',
        name: 'ai-studio-app-detail',
        meta: {
          title: 'AI 应用配置',
          permissions: ['ai_studio:access'],
          activeMenu: 'ai-studio',
          hidden: true,
        },
        component: () => import('@/views/ai/studio/detail.vue'),
      },
      {
        path: 'studio/capabilities/:capabilityKey',
        name: 'ai-studio-capability-detail',
        meta: {
          title: 'AI 能力配置',
          permissions: ['ai_studio:access'],
          activeMenu: 'ai-studio',
          hidden: true,
        },
        component: () => import('@/views/ai/studio/detail.vue'),
      },
    ],
  },
];

export default routes;
