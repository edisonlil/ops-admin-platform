import { getConfigFileName } from '../../getConfigFileName';
import { getEnvConfig } from '../../utils';
import { GLOB_CONFIG_FILE_NAME } from '../../constant';
import type { Plugin } from 'vite';

function buildAppConfigCode() {
  const config = getEnvConfig();
  const configName = getConfigFileName(config);
  const windowConf = `window.${configName}`;
  return `${windowConf}=${JSON.stringify(config)};
Object.freeze(${windowConf});
Object.defineProperty(window,"${configName}",{configurable:false,writable:false,});`;
}

export function configAppConfigPlugin(): Plugin {
  return {
    name: 'ops-admin-app-config',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = req.url?.split('?')[0];
        if (url !== `/${GLOB_CONFIG_FILE_NAME}`) {
          next();
          return;
        }
        res.statusCode = 200;
        res.setHeader('Content-Type', 'application/javascript; charset=utf-8');
        res.end(buildAppConfigCode());
      });
    },
  };
}
