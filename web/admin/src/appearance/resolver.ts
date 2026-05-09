import type { AppearanceTokens, ResolvedAppearance, TokenValidationError } from './types';

const REF_PATTERN = /^\{([^{}]+)\}$/;

function flattenTokens(value: unknown, path: string[] = [], result: Record<string, unknown> = {}) {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    Object.entries(value as Record<string, unknown>).forEach(([key, item]) => {
      flattenTokens(item, [...path, key], result);
    });
    return result;
  }

  const fullPath = path.join('.');
  result[fullPath] = value;
  const shortName = path[path.length - 1];
  if (!(shortName in result)) {
    result[shortName] = value;
  }
  return result;
}

function resolveValue(
  value: unknown,
  tokenMap: Record<string, unknown>,
  path: string,
  stack: string[],
  errors: TokenValidationError[]
): unknown {
  if (Array.isArray(value)) {
    return value.map((item, index) =>
      resolveValue(item, tokenMap, `${path}.${index}`, stack, errors)
    );
  }

  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, item]) => [
        key,
        resolveValue(item, tokenMap, `${path}.${key}`, stack, errors),
      ])
    );
  }

  if (typeof value !== 'string') return value;
  const match = value.match(REF_PATTERN);
  if (!match) return value;

  const tokenName = match[1];
  if (stack.includes(tokenName)) {
    errors.push({
      path,
      code: 'TOKEN_REFERENCE_CYCLE',
      message: `变量引用存在循环：${[...stack, tokenName].join(' -> ')}`,
    });
    return value;
  }

  if (!(tokenName in tokenMap)) {
    errors.push({
      path,
      code: 'TOKEN_REFERENCE_MISSING',
      message: `找不到引用的变量：${tokenName}`,
    });
    return value;
  }

  return resolveValue(tokenMap[tokenName], tokenMap, path, [...stack, tokenName], errors);
}

export function resolveAppearanceTokens(tokens: AppearanceTokens): ResolvedAppearance {
  const errors: TokenValidationError[] = [];
  const tokenMap = flattenTokens(tokens);
  const resolved = resolveValue(tokens, tokenMap, 'appearance', [], errors) as AppearanceTokens;
  return {
    tokens: resolved,
    errors,
  };
}
