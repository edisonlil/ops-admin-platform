import type { ComponentTokens } from '../types';

export const defaultDarkComponentTokens: Partial<
  Record<keyof ComponentTokens, Record<string, string>>
> = {
  StatusTag: {
    successText: '#86efac',
    successBg: '#052e1a',
    successBorder: '#166534',
    warningText: '#fcd34d',
    warningBg: '#3b2a05',
    warningBorder: '#92400e',
    errorText: '#fb7185',
    errorBg: '#3f111f',
    errorBorder: '#9f1239',
    infoText: '#93c5fd',
    infoBg: '{primaryColorSoft}',
    infoBorder: '#1d4ed8',
    neutralText: '{textColorSecondary}',
    neutralBg: '{surfaceMutedColor}',
    neutralBorder: '{borderColorBase}',
  },
  TableAction: {
    dangerTextColor: '#fb7185',
    dangerBorderColor: '#e11d48',
  },
  Alert: {
    infoBg: '{primaryColorSoft}',
    infoText: '{textColorBase}',
    infoBorder: '#1d4ed8',
    successBg: '#052e1a',
    successText: '#dcfce7',
    successBorder: '#166534',
    warningBg: '#3b2a05',
    warningText: '#fef3c7',
    warningBorder: '#92400e',
    errorBg: '#3f111f',
    errorText: '#ffe4e6',
    errorBorder: '#9f1239',
  },
};
