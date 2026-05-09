import type { ListPageSchema } from './types';

export function defineListPage<Row, Query = Record<string, unknown>>(
  schema: ListPageSchema<Row, Query>
): ListPageSchema<Row, Query> {
  return Object.freeze({
    density: 'comfortable',
    variant: 'enterprise',
    filters: [],
    toolbar: {},
    ...schema,
  });
}
