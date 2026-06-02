import assert from 'node:assert/strict';
import type { AppearanceTokens, TokenValidationError } from '../src/appearance/types';
import { resolveAppearanceTokens } from '../src/appearance/resolver';
import { validateAppearanceTokens } from '../src/appearance/validators';
import { createNaiveThemeOverrides } from '../src/appearance/naiveAdapter';
import { createAppearanceCssVars } from '../src/appearance/cssVarAdapter';
import { createLayoutConfig } from '../src/appearance/layoutAdapter';
import { mergeAppearanceTokens } from '../src/appearance/mergeTokens';
import { defaultPreset } from '../src/appearance/presets/default';
import { primevueLikePreset } from '../src/appearance/presets/primevueLike';

function cloneTokens(tokens: AppearanceTokens): AppearanceTokens {
  return JSON.parse(JSON.stringify(tokens));
}

function expectError(errors: TokenValidationError[], code: string) {
  assert.ok(
    errors.some((error) => error.code === code),
    `Expected validation error ${code}, got ${errors.map((error) => error.code).join(', ')}`
  );
}

function testResolverReferences() {
  const { tokens, errors } = resolveAppearanceTokens(defaultPreset.tokens);

  assert.deepEqual(errors, []);
  assert.equal(tokens.semantic.primaryColor, '#2d8cf0');
  assert.equal(tokens.semantic.primaryColorPressed, '#1d73d4');
  assert.equal(tokens.component.Button.primaryBg, '#2d8cf0');
  assert.equal(tokens.component.Button.primaryBgPressed, '#1d73d4');
  assert.equal(tokens.component.Card.radius, '4px');
}

function testResolverMissingReference() {
  const tokens = cloneTokens(defaultPreset.tokens);
  tokens.semantic.primaryColor = '{missingPrimary}';

  const result = resolveAppearanceTokens(tokens);

  expectError(result.errors, 'TOKEN_REFERENCE_MISSING');
  assert.equal(result.tokens.semantic.primaryColor, '{missingPrimary}');
}

function testResolverCycleReference() {
  const tokens = cloneTokens(defaultPreset.tokens);
  tokens.primitive.blue500 = '{primaryColor}';
  tokens.semantic.primaryColor = '{blue500}';

  const result = resolveAppearanceTokens(tokens);

  expectError(result.errors, 'TOKEN_REFERENCE_CYCLE');
}

function testValidators() {
  const tokens = cloneTokens(defaultPreset.tokens);
  tokens.semantic.primaryColor = 'not-a-color';
  tokens.component.Button.height = '36';
  tokens.component.Dialog.padding = '28px 32px';
  tokens.component.Alert.padding = '12px 16px';
  tokens.layout.density = 'dense' as AppearanceTokens['layout']['density'];
  tokens.layout.menuWidth = -1;

  const errors = validateAppearanceTokens(tokens);

  expectError(errors, 'TOKEN_INVALID_COLOR');
  expectError(errors, 'TOKEN_INVALID_SIZE');
  expectError(errors, 'TOKEN_INVALID_ENUM');
  expectError(errors, 'TOKEN_INVALID_NUMBER');
}

function testAdapters() {
  const { tokens, errors } = resolveAppearanceTokens(primevueLikePreset.tokens);
  assert.deepEqual(errors, []);

  const themeOverrides = createNaiveThemeOverrides(tokens);
  const cssVars = createAppearanceCssVars(tokens);
  const layoutConfig = createLayoutConfig(tokens);

  assert.equal(themeOverrides.common?.primaryColor, '#2563eb');
  assert.equal(themeOverrides.common?.primaryColorPressed, '#1d4ed8');
  assert.equal(themeOverrides.Button?.colorPrimary, '#2563eb');
  assert.equal(themeOverrides.Button?.colorPressedPrimary, '#1d4ed8');
  assert.ok(themeOverrides.DataTable?.thColor);
  assert.equal(themeOverrides.DataTable?.tdColor, '#ffffff');
  assert.equal(themeOverrides.DataTable?.tdTextColor, '#0f172a');
  assert.equal(themeOverrides.DataTable?.tdColorSelected, '#eff6ff');
  assert.equal(themeOverrides.DataTable?.tdHeightMedium, '46px');
  assert.equal(themeOverrides.DataTable?.thHeightMedium, '46px');
  assert.equal(themeOverrides.DataTable?.tdPaddingMedium, '8px 12px');
  assert.equal(themeOverrides.Menu?.itemColorActive, '#eff6ff');
  assert.equal(themeOverrides.Menu?.itemColorHover, '#f1f5f9');
  assert.equal(themeOverrides.Menu?.color, '#ffffff');
  assert.equal(themeOverrides.Menu?.colorInverted, '#0f172a');
  assert.equal(themeOverrides.Menu?.itemColorActiveInverted, '#2563eb');
  assert.equal(themeOverrides.Menu?.itemColorHoverInverted, '#0000');
  assert.equal(themeOverrides.Menu?.itemTextColorActive, '#2563eb');
  assert.equal(themeOverrides.Menu?.itemTextColorActiveInverted, '#ffffff');
  assert.equal(themeOverrides.LoadingBar?.colorLoading, '#2563eb');
  assert.equal(themeOverrides.Tag?.color, '#f1f5f9');
  assert.equal(themeOverrides.Tag?.textColor, '#334155');
  assert.equal(themeOverrides.Tag?.colorSuccess, '#ecfdf5');
  assert.equal(themeOverrides.Tag?.textColorSuccess, '#047857');
  assert.equal(themeOverrides.Tag?.colorError, '#fff1f2');
  assert.equal(themeOverrides.Tag?.textColorError, '#be123c');
  assert.equal(cssVars['--app-page-bg'], '#f8fafc');
  assert.equal(cssVars['--app-primary-pressed-color'], '#1d4ed8');
  assert.equal(cssVars['--app-menu-width'], `${tokens.layout.menuWidth}px`);
  assert.equal(cssVars['--app-menu-bg'], '#ffffff');
  assert.equal(cssVars['--app-menu-bg-inverted'], '#0f172a');
  assert.equal(cssVars['--app-table-radius'], '6px');
  assert.equal(cssVars['--app-table-action-button-height'], '32px');
  assert.equal(cssVars['--app-status-success-bg'], '#ecfdf5');
  assert.equal(layoutConfig.contentPadding, 14);
}

function testDarkSemanticMerge() {
  const lightTokens = mergeAppearanceTokens(primevueLikePreset, {}, {}, false);
  const darkTokens = mergeAppearanceTokens(primevueLikePreset, {}, {}, true);
  const overriddenDarkTokens = mergeAppearanceTokens(
    primevueLikePreset,
    { darkSemantic: { pageBgColor: '#020617' } },
    {},
    true
  );

  assert.equal(resolveAppearanceTokens(lightTokens).tokens.semantic.pageBgColor, '#f8fafc');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.semantic.pageBgColor, '#0f172a');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.component.Menu.itemBgActive, '#172554');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.component.Menu.itemBgHover, '#1e293b');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.component.Menu.bgColor, '#0f172a');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.component.Menu.bgColorInverted, '#0f172a');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.component.Menu.itemTextColorActiveInverted, '#ffffff');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.component.Menu.itemBgActiveInverted, '#1e3a8a');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.component.Menu.itemBgHoverInverted, '#1e293b');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.component.TableAction.disabledTextColor, '#94a3b8');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.component.TableAction.disabledBgColor, '#0f172a');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.component.DataTable.bodyBg, '#111827');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.component.DataTable.headerBg, '#1e293b');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.component.DataTable.rowHoverBg, '#172554');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.component.StatusTag.successBg, '#052e1a');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.component.StatusTag.successText, '#86efac');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.component.StatusTag.errorBg, '#3f111f');
  assert.equal(resolveAppearanceTokens(darkTokens).tokens.component.Alert.successBg, '#052e1a');
  assert.equal(resolveAppearanceTokens(overriddenDarkTokens).tokens.semantic.pageBgColor, '#020617');
}

testResolverReferences();
testResolverMissingReference();
testResolverCycleReference();
testValidators();
testAdapters();
testDarkSemanticMerge();

console.log('appearance tests passed');
