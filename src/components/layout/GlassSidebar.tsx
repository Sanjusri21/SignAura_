import React from 'react';
import { NavigationTab } from '../../types';
import { GlassNavigationRail } from './GlassNavigationRail';

interface GlassSidebarProps {
  activeTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const GlassSidebar: React.FC<GlassSidebarProps> = ({
  activeTab,
  onSelectTab
}) => {
  return <GlassNavigationRail activeTab={activeTab} onSelectTab={onSelectTab} />;
};
