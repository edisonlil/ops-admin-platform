export interface OpsAdminLayoutConfig {
  headerHeight: number;
  tabsHeight: number;
  menuWidth: number;
  collapsedMenuWidth: number;
  contentPadding: number;
  density: 'compact' | 'default' | 'comfortable';
}

export interface OpsAdminLayoutModule {
  layoutComponent: unknown;
  parentLayoutComponent?: unknown;
}
