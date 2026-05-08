export interface OpsAdminMenuNode {
  key: string;
  label?: string;
  children?: OpsAdminMenuNode[];
  [key: string]: unknown;
}

export function filterOpsAdminMenuTree(
  items: OpsAdminMenuNode[],
  allowMenuKey: (key: string) => boolean
): OpsAdminMenuNode[] {
  return items.reduce<OpsAdminMenuNode[]>((list, item) => {
    const children = filterOpsAdminMenuTree(item.children || [], allowMenuKey);
    if (!allowMenuKey(item.key) && !children.length) {
      return list;
    }
    list.push({
      ...item,
      ...(children.length ? { children } : {}),
    });
    return list;
  }, []);
}
