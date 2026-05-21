import type { ListRuntimeState } from './types';

export function runtimeListParams(state?: ListRuntimeState, defaults: { page?: number; pageSize?: number } = {}) {
  return {
    page: state?.pagination?.page ?? defaults.page ?? 1,
    page_size: state?.pagination?.pageSize ?? defaults.pageSize ?? 20,
    sort_by: state?.sort?.sort_by,
    sort_dir: state?.sort?.sort_dir,
  };
}

export function runtimeSortParams(state?: ListRuntimeState) {
  return {
    sort_by: state?.sort?.sort_by,
    sort_dir: state?.sort?.sort_dir,
  };
}
