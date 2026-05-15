import { createAlova } from 'alova';
import VueHook from 'alova/vue';
import adapterFetch from 'alova/fetch';
import { createAlovaMockAdapter } from '@alova/mock';
import { isString } from 'lodash-es';
import mocks from './mocks';
import { useUser } from '@/store/modules/user';
import { storage } from '@/utils/Storage';
import { useGlobSetting, useLocalSetting } from '@/hooks/setting';
import { PageEnum } from '@/enums/pageEnum';
import { ResultEnum } from '@/enums/httpEnum';
import { isUrl } from '@/utils';
import { ACCESS_TOKEN, CURRENT_USER, IS_SCREENLOCKED } from '@/store/mutation-types';

const { apiUrl, urlPrefix } = useGlobSetting();

const { useMock, loggerMock } = useLocalSetting();

function clearAuthAndRedirect() {
  storage.remove(ACCESS_TOKEN);
  storage.remove(CURRENT_USER);
  storage.remove(IS_SCREENLOCKED);
  const loginPath = PageEnum.BASE_LOGIN;
  if (window.location.pathname !== loginPath) {
    window.location.href = loginPath;
  }
}

const mockAdapter = createAlovaMockAdapter([...mocks], {
  // 全局控制是否启用mock接口，默认为true
  enable: useMock,

  // 非模拟请求适配器，用于未匹配mock接口时发送请求
  httpAdapter: adapterFetch(),

  // mock接口响应延迟，单位毫秒
  delay: 1000,

  // 自定义打印mock接口请求信息
  // mockRequestLogger: (res) => {
  //   loggerMock && console.log(`Mock Request ${res.url}`, res);
  // },
  mockRequestLogger: loggerMock,
  onMockError(error, currentMethod) {
    console.error('🚀 ~ onMockError ~ currentMethod:', currentMethod);
    console.error('🚀 ~ onMockError ~ error:', error);
  },
});

export const Alova = createAlova({
  baseURL: apiUrl,
  statesHook: VueHook,
  // 关闭全局请求缓存
  // cacheFor: null,
  // 全局缓存配置
  // cacheFor: {
  //   POST: {
  //     mode: 'memory',
  //     expire: 60 * 10 * 1000
  //   },
  //   GET: {
  //     mode: 'memory',
  //     expire: 60 * 10 * 1000
  //   },
  //   HEAD: 60 * 10 * 1000 // 统一设置HEAD请求的缓存模式
  // },
  // 在开发环境开启缓存命中日志
  cacheLogger: process.env.NODE_ENV === 'development',
  requestAdapter: mockAdapter,
  beforeRequest(method) {
    const userStore = useUser();
    const token = userStore.getToken;
    // 添加 token 到请求头
    if (!method.meta?.ignoreToken && token) {
      method.config.headers['token'] = token;
      method.config.headers['Authorization'] = `Bearer ${token}`;
    }
    method.config.credentials = 'include';
    // 处理 api 请求前缀
    const isUrlStr = isUrl(method.url as string);
    if (!isUrlStr && urlPrefix) {
      method.url = `${urlPrefix}${method.url}`;
    }
    if (!isUrlStr && apiUrl && isString(apiUrl)) {
      method.url = `${apiUrl}${method.url}`;
    }
  },
  responded: {
    onSuccess: async (response, method) => {
      let res: any = response.body;
      try {
        const isParsedBody =
          res &&
          typeof res === 'object' &&
          !('getReader' in res) &&
          !('pipeTo' in res) &&
          ('success' in res || 'code' in res || 'data' in res || 'result' in res || 'message' in res);

        if (isParsedBody) {
          // Some adapters expose the parsed JSON on body. Reading json() again can fail.
          res = response.body;
        } else if (typeof res === 'string' && res.length > 0) {
          res = JSON.parse(res);
        } else if (response.json) {
          res = await response.json();
        } else {
          res = response.body;
        }
      } catch (error) {
        const errorMessage = response.status >= 500 ? '服务器内部错误，请稍后重试' : response.statusText || 'Request failed';
        // @ts-ignore
        window.$message?.error(errorMessage);
        throw new Error(errorMessage);
      }

      // 是否返回原生响应头 比如：需要获取响应头时使用该属性
      if (method.meta?.isReturnNativeResponse) {
        return res;
      }
      // 请根据自身情况修改数据结构
      const { success, message, code, data, errors, result } = res || {};

      // 不进行任何处理，直接返回
      // 用于需要直接获取 code、result、 message 这些信息时开启
      if (method.meta?.isTransformResponse === false) {
        return data ?? res.data;
      }

      // @ts-ignore
      const Message = window.$message;
      // @ts-ignore
      const Modal = window.$dialog;

      const LoginPath = PageEnum.BASE_LOGIN;
      if (success === true) {
        return data;
      }
      if (ResultEnum.SUCCESS === code) {
        return result;
      }
      if (response.status === 401 || code === 'UNAUTHORIZED') {
        const errorMessage = message || errors?.[0]?.message || res?.detail || '登录身份已失效';
        Message?.error(errorMessage);
        clearAuthAndRedirect();
        throw new Error(errorMessage);
      }
      if (success === false) {
        const errorMessage = message || errors?.[0]?.message || res?.detail || 'Request failed';
        Message?.error(errorMessage);
        throw new Error(errorMessage);
      }
      // 需要登录
      if (code === 912) {
        Modal?.warning({
          title: '提示',
          content: '登录身份已失效，请重新登录!',
          okText: '确定',
          closable: false,
          maskClosable: false,
          onOk: async () => {
            storage.clear();
            window.location.href = LoginPath;
          },
        });
      } else {
        // 可按需处理错误 一般情况下不是 912 错误，不一定需要弹出 message
        Message?.error(message);
        throw new Error(message);
      }
    },
  },
});

// 项目，多个不同 api 地址，可导出多个实例
// export const AlovaTwo = createAlova({
//   baseURL: 'http://localhost:9001',
// });
