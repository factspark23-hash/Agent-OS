import React from 'react';
import { useAppStore } from '../store/useAppStore';
import type { TabId } from '../types';
import {
  LayoutDashboard, Terminal, Key, Globe, UserCheck, Zap, Settings, Activity,
} from 'lucide-react';

const NAV_ITEMS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
  { id: 'command', label: 'Command', icon: <Terminal size={20} /> },
  { id: 'apikeys', label: 'API Keys', icon: <Key size={20} /> },
  { id: 'browser', label: 'Browser', icon: <Globe size={20} /> },
  { id: 'handoff', label: 'Handoff', icon: <UserCheck size={20} /> },
  { id: 'swarm', label: 'Swarm', icon: <Zap size={20} /> },
  { id: 'settings', label: 'Settings', icon: <Settings size={20} /> },
];

export function Sidebar() {
  const activeTab = useAppStore((s) => s.activeTab);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const serverStatus = useAppStore((s) => s.serverStatus);

  return (
    <aside className="w-64 h-full flex flex-col glass border-r border-white/10">
      {/* Logo */}
      <div className="p-5 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center glow-brand">
            <Activity size={22} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gradient">Agent-OS</h1>
            <p className="text-[10px] text-white/40 tracking-wider uppercase">AI Browser Automation</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1 overflow-auto">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
              activeTab === item.id
                ? 'bg-brand-600/20 text-brand-400 border border-brand-500/30 glow-brand'
                : 'text-white/50 hover:text-white/80 hover:bg-white/5'
            }`}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      {/* Server Status */}
      <div className="p-4 border-t border-white/10">
        <div className="flex items-center gap-2 text-xs">
          <div
            className={`w-2 h-2 rounded-full ${
              serverStatus.online ? 'bg-green-500 animate-pulse-slow' : 'bg-red-500'
            }`}
          />
          <span className="text-white/50">
            {serverStatus.online ? 'Server Online' : 'Server Offline'}
          </span>
        </div>
        {serverStatus.online && serverStatus.version && (
          <p className="text-[10px] text-white/30 mt-1 ml-4">v{serverStatus.version}</p>
        )}
      </div>
    </aside>
  );
}
