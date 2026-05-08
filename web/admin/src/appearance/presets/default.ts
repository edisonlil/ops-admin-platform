import type { AppearancePreset } from '../types';
import { defaultPrimitiveTokens } from '../tokens/primitive';
import { defaultSemanticTokens } from '../tokens/semantic';
import { defaultDarkSemanticTokens } from '../tokens/darkSemantic';
import { defaultComponentTokens } from '../tokens/component';
import { defaultLayoutTokens } from '../tokens/layout';

export const defaultPreset: AppearancePreset = {
  id: 'default',
  name: '默认风格',
  description: '尽量保持当前后台默认外观，只做必要的运行时主题覆盖。',
  skinClass: '',
  tokens: {
    primitive: defaultPrimitiveTokens,
    semantic: defaultSemanticTokens,
    component: defaultComponentTokens,
    layout: defaultLayoutTokens,
  },
  darkSemantic: defaultDarkSemanticTokens,
};
