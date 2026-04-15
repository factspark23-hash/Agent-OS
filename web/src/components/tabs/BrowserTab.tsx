import React, { useState, useCallback } from 'react';
import { useAppStore } from '../../store/useAppStore';
import {
  Globe, Navigation, Camera, RotateCw, ArrowLeft, ArrowRight, ExternalLink,
  Loader2, Monitor, Maximize2,
} from 'lucide-react';

export function BrowserTab() {
  const [urlInput, setUrlInput] = useState('');
  const browserState = useAppStore((s) => s.browserState);
  const setBrowserState = useAppStore((s) => s.setBrowserState);

  const handleNavigate = useCallback(() => {
    if (!urlInput.trim()) return;
    let url = urlInput.trim();
    if (!url.startsWith('http')) url = 'https://' + url;
    setBrowserState({ url, isLoading: true, title: url });
    // Simulate loading
    setTimeout(() => setBrowserState({ isLoading: false }), 1500);
  }, [urlInput, setBrowserState]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleNavigate();
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h2 className="text-2xl font-bold text-gradient">Browser Control</h2>
        <p className="text-white/40 text-sm mt-1">Control the stealth browser — navigate, screenshot, interact</p>
      </div>

      {/* URL Bar */}
      <div className="card">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <button className="p-2 rounded-lg hover:bg-white/10 text-white/40 hover:text-white/60 transition-colors">
              <ArrowLeft size={16} />
            </button>
            <button className="p-2 rounded-lg hover:bg-white/10 text-white/40 hover:text-white/60 transition-colors">
              <ArrowRight size={16} />
            </button>
            <button
              onClick={() => setBrowserState({ isLoading: true })}
              className="p-2 rounded-lg hover:bg-white/10 text-white/40 hover:text-white/60 transition-colors"
            >
              <RotateCw size={16} className={browserState.isLoading ? 'animate-spin' : ''} />
            </button>
          </div>
          <div className="flex-1 relative">
            <Globe size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
            <input
              type="text"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Enter URL..."
              className="input-field pl-9 text-sm"
            />
          </div>
          <button onClick={handleNavigate} className="btn-primary flex items-center gap-2 text-sm">
            <Navigation size={14} />
            Go
          </button>
        </div>
      </div>

      {/* Browser Viewport */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Monitor size={14} className="text-white/40" />
            <span className="text-xs text-white/40">
              {browserState.url ? browserState.title || browserState.url : 'No page loaded'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {browserState.isLoading && (
              <span className="badge-warning flex items-center gap-1">
                <Loader2 size={10} className="animate-spin" /> Loading
              </span>
            )}
            <button className="p-1.5 rounded-lg hover:bg-white/10 text-white/30 hover:text-white/60 transition-colors">
              <Maximize2 size={14} />
            </button>
          </div>
        </div>

        {/* Screenshot Area */}
        <div className="aspect-video rounded-xl bg-surface-900 border border-white/5 flex items-center justify-center overflow-hidden">
          {browserState.screenshot ? (
            <img
              src={`data:image/png;base64,${browserState.screenshot}`}
              alt="Browser screenshot"
              className="w-full h-full object-contain"
            />
          ) : browserState.isLoading ? (
            <div className="flex flex-col items-center gap-3">
              <Loader2 size={40} className="text-brand-400 animate-spin" />
              <p className="text-sm text-white/30">Loading page...</p>
            </div>
          ) : browserState.url ? (
            <div className="flex flex-col items-center gap-3">
              <Globe size={48} className="text-white/10" />
              <p className="text-sm text-white/30">{browserState.url}</p>
              <p className="text-xs text-white/20">Connect to Agent-OS server for live browser view</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <Globe size={48} className="text-white/10" />
              <p className="text-sm text-white/30">Enter a URL to browse</p>
              <p className="text-xs text-white/20">Navigate to any website using the stealth browser</p>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Take Screenshot', icon: <Camera size={16} />, action: () => {} },
          { label: 'Open External', icon: <ExternalLink size={16} />, action: () => browserState.url && window.open(browserState.url, '_blank') },
          { label: 'Refresh', icon: <RotateCw size={16} />, action: () => setBrowserState({ isLoading: true }) },
        ].map((btn) => (
          <button
            key={btn.label}
            onClick={btn.action}
            className="btn-secondary flex items-center justify-center gap-2 py-3"
          >
            {btn.icon}
            <span className="text-sm">{btn.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
