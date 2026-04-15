import React from 'react';
import { Sidebar } from './components/Sidebar';
import { TabView } from './components/TabView';
import { useAppStore } from './store/useAppStore';

export default function App() {
  const theme = useAppStore((s) => s.theme);

  return (
    <div className={`${theme === 'dark' ? 'dark' : ''}`}>
      <div className="flex h-screen bg-surface-950 text-white overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <TabView />
        </main>
      </div>
    </div>
  );
}
