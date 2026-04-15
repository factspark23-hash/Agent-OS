import React from 'react';
import { useAppStore } from '../store/useAppStore';
import { DashboardTab } from './tabs/DashboardTab';
import { CommandTab } from './tabs/CommandTab';
import { ApiKeysTab } from './tabs/ApiKeysTab';
import { BrowserTab } from './tabs/BrowserTab';
import { HandoffTab } from './tabs/HandoffTab';
import { SwarmTab } from './tabs/SwarmTab';
import { SettingsTab } from './tabs/SettingsTab';

const TABS: Record<string, React.FC> = {
  dashboard: DashboardTab,
  command: CommandTab,
  apikeys: ApiKeysTab,
  browser: BrowserTab,
  handoff: HandoffTab,
  swarm: SwarmTab,
  settings: SettingsTab,
};

export function TabView() {
  const activeTab = useAppStore((s) => s.activeTab);
  const Component = TABS[activeTab] || DashboardTab;

  return (
    <div className="p-6 animate-in">
      <Component />
    </div>
  );
}
