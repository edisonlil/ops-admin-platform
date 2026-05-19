import type { ListRuntimeState } from './types';

export function runtimeListParams(state?: ListRuntimeState) {
  return {
    page: state?.pagination?.page,
    page_size: state?.pagination?.pageSize,
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
