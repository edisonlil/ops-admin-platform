import type { DetailPageSchema } from './types';

export function defineDetailPage<T>(schema: DetailPageSchema<T>): DetailPageSchema<T> {
  return Object.freeze({
    density: 'comfortable',
    variant: 'enterprise',
    ...schema,
  });
}
