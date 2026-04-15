import React, { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import {
  Zap, Search, Users, Activity, Clock, CheckCircle, XCircle, Loader2,
  Settings, BarChart3, Layers,
} from 'lucide-react';

export function SwarmTab() {
  const [query, setQuery] = useState('');
  const [swarmSize, setSwarmSize] = useState(5);
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<any>(null);

  const swarmAgents = useAppStore((s) => s.swarmAgents);
  const setSwarmAgents = useAppStore((s) => s.setSwarmAgents);
  const swarmSessions = useAppStore((s) => s.swarmSessions);
  const addSwarmSession = useAppStore((s) => s.addSwarmSession);
  const updateSwarmSession = useAppStore((s) => s.updateSwarmSession);

  const handleSearch = async () => {
    if (!query.trim()) return;
    const sessionId = crypto.randomUUID();

    addSwarmSession({
      id: sessionId,
      query: query.trim(),
      status: 'routing',
      agents: swarmAgents.slice(0, swarmSize).map(a => a.key),
      resultsCount: 0,
      startedAt: new Date().toISOString(),
    });

    setIsSearching(true);
    setSwarmAgents(swarmAgents.map(a => ({ ...a, status: 'searching' as const })));
    updateSwarmSession(sessionId, { status: 'searching' });

    // Simulate search
    setTimeout(() => {
      updateSwarmSession(sessionId, { status: 'aggregating' });
    }, 1000);

    setTimeout(() => {
      setSwarmAgents(swarmAgents.map(a => ({ ...a, status: 'completed' as const })));
      updateSwarmSession(sessionId, {
        status: 'completed',
        completedAt: new Date().toISOString(),
        resultsCount: Math.floor(Math.random() * 15) + 5,
      });
      setSearchResults({
        query: query.trim(),
        totalResults: Math.floor(Math.random() * 15) + 5,
        agents: swarmSize,
        time: (Math.random() * 3 + 1).toFixed(2) + 's',
      });
      setIsSearching(false);
      setQuery('');
    }, 3000);
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h2 className="text-2xl font-bold text-gradient">Swarm Search</h2>
        <p className="text-white/40 text-sm mt-1">Parallel multi-agent search with 3-tier query routing</p>
      </div>

      {/* Search Bar */}
      <div className="card glow-brand">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search anything — news, prices, tech docs, research..."
              className="input-field pl-10 text-sm"
              disabled={isSearching}
            />
          </div>
          <button onClick={handleSearch} disabled={isSearching || !query.trim()} className="btn-primary flex items-center gap-2">
            {isSearching ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
            {isSearching ? 'Searching...' : 'Swarm Search'}
          </button>
        </div>

        {/* Swarm Size Control */}
        <div className="mt-4 flex items-center gap-4">
          <span className="text-xs text-white/40">Swarm Size:</span>
          <div className="flex items-center gap-2">
            {[1, 3, 5, 10, 20, 50].map((size) => (
              <button
                key={size}
                onClick={() => setSwarmSize(size)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  swarmSize === size
                    ? 'bg-brand-600 text-white'
                    : 'bg-white/5 text-white/40 hover:text-white/60'
                }`}
              >
                {size}
              </button>
            ))}
          </div>
          <span className="text-[10px] text-white/20">agents</span>
        </div>
      </div>

      {/* Search Results */}
      {searchResults && (
        <div className="card animate-in glow-success">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-green-400 flex items-center gap-2">
              <CheckCircle size={14} /> Search Complete
            </h3>
            <span className="text-xs text-white/30">{searchResults.time}</span>
          </div>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="text-center p-3 rounded-xl bg-white/5">
              <p className="text-2xl font-bold text-brand-400">{searchResults.totalResults}</p>
              <p className="text-[10px] text-white/30">Results</p>
            </div>
            <div className="text-center p-3 rounded-xl bg-white/5">
              <p className="text-2xl font-bold text-yellow-400">{searchResults.agents}</p>
              <p className="text-[10px] text-white/30">Agents Used</p>
            </div>
            <div className="text-center p-3 rounded-xl bg-white/5">
              <p className="text-2xl font-bold text-green-400">95%</p>
              <p className="text-[10px] text-white/30">Deduped</p>
            </div>
          </div>
          <p className="text-xs text-white/30">
            Query: <span className="text-white/50">"{searchResults.query}"</span>
          </p>
        </div>
      )}

      {/* Agent Pool Status */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider">Agent Pool</h3>
          <span className="text-xs text-white/30">{swarmAgents.length} agents</span>
        </div>
        <div className="space-y-2">
          {swarmAgents.map((agent) => (
            <div key={agent.key} className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-white/8 transition-all">
              <div className="flex items-center gap-3">
                <div className={`w-2.5 h-2.5 rounded-full ${
                  agent.status === 'idle' ? 'bg-green-500' :
                  agent.status === 'searching' ? 'bg-yellow-500 animate-pulse' :
                  agent.status === 'completed' ? 'bg-blue-500' : 'bg-red-500'
                }`} />
                <div>
                  <p className="text-sm font-medium text-white/70">{agent.name}</p>
                  <p className="text-[10px] text-white/30">{agent.expertise} · Priority {agent.priority}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex gap-1">
                  {agent.sources.slice(0, 2).map((s) => (
                    <span key={s} className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-white/30">{s}</span>
                  ))}
                </div>
                <span className={`text-[10px] font-medium ${
                  agent.status === 'idle' ? 'text-green-400' :
                  agent.status === 'searching' ? 'text-yellow-400' :
                  agent.status === 'completed' ? 'text-blue-400' : 'text-red-400'
                }`}>
                  {agent.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 3-Tier Router Explanation */}
      <div className="card">
        <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4">3-Tier Query Router</h3>
        <div className="space-y-3">
          {[
            {
              tier: 'Tier 1',
              name: 'Rule-Based',
              desc: '33 regex patterns across 4 categories — instant classification with 0.7+ confidence',
              icon: <Layers size={16} />,
              color: 'text-green-400',
              bg: 'bg-green-500/10',
            },
            {
              tier: 'Tier 2',
              name: 'LLM Fallback',
              desc: 'Uses your API key for ~50 token classification when rule-based is uncertain',
              icon: <Activity size={16} />,
              color: 'text-yellow-400',
              bg: 'bg-yellow-500/10',
            },
            {
              tier: 'Tier 3',
              name: 'Conservative',
              desc: 'Always returns NEEDS_WEB — better to over-search than miss critical info',
              icon: <BarChart3 size={16} />,
              color: 'text-red-400',
              bg: 'bg-red-500/10',
            },
          ].map((tier) => (
            <div key={tier.tier} className="flex items-start gap-3 p-3 rounded-xl bg-white/5">
              <div className={`w-8 h-8 rounded-lg ${tier.bg} flex items-center justify-center ${tier.color} flex-shrink-0`}>
                {tier.icon}
              </div>
              <div>
                <p className={`text-xs font-semibold ${tier.color}`}>{tier.tier}: {tier.name}</p>
                <p className="text-[11px] text-white/30 mt-0.5">{tier.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Search History */}
      {swarmSessions.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-4">Search History</h3>
          <div className="space-y-2">
            {swarmSessions.slice(0, 10).map((session) => (
              <div key={session.id} className="flex items-center justify-between p-3 rounded-xl bg-white/5">
                <div className="flex items-center gap-3">
                  {session.status === 'completed' ? (
                    <CheckCircle size={14} className="text-green-400" />
                  ) : session.status === 'failed' ? (
                    <XCircle size={14} className="text-red-400" />
                  ) : (
                    <Loader2 size={14} className="text-yellow-400 animate-spin" />
                  )}
                  <div>
                    <p className="text-sm text-white/60">{session.query}</p>
                    <p className="text-[10px] text-white/20">
                      {session.agents.length} agents · {session.resultsCount} results
                    </p>
                  </div>
                </div>
                <span className="text-[10px] text-white/20">{new Date(session.startedAt).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
