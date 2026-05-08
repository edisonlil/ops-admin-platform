import type { SemanticTokens } from '../types';
import { defaultSemanticTokens } from './semantic';

export const defaultDarkSemanticTokens: SemanticTokens = {
  ...defaultSemanticTokens,
  primaryColor: '{blue500}',
  primaryColorHover: '{blue500}',
  primaryColorPressed: '{blue600}',
  primaryColorSoft: '#102a43',
  successColor: '{green500}',
  warningColor: '{amber500}',
  errorColor: '{red500}',
  infoColor: '{cyan500}',
  textColorBase: '#f8fafc',
  textColorSecondary: '#cbd5e1',
  textColorMuted: '#94a3b8',
  pageBgColor: '#0f172a',
  surfaceColor: '#111827',
  surfaceMutedColor: '#1f2937',
  borderColorBase: '#334155',
  borderColorStrong: '#475569',
  shadowBase: '0 10px 24px rgb(0 0 0 / 22%)',
};
