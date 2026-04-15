import { create } from 'zustand';
import type { TabId, APIKey, ChatMessage, HandoffSession, BrowserState, AgentSession, SwarmAgent, ServerStatus } from '../types';
import { detectProvider, maskKey } from '../config/providers';

interface AppState {
  // Navigation
  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;

  // API Keys
  apiKeys: APIKey[];
  addApiKey: (key: string, model?: string) => void;
  removeApiKey: (id: string) => void;
  activeProvider: string | null;
  activeModel: string | null;

  // Chat / Command
  chatMessages: ChatMessage[];
  addChatMessage: (msg: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  isProcessing: boolean;
  setIsProcessing: (v: boolean) => void;

  // Browser
  browserState: BrowserState;
  setBrowserState: (s: Partial<BrowserState>) => void;

  // Handoff
  handoffSessions: HandoffSession[];
  addHandoffSession: (s: HandoffSession) => void;
  updateHandoffSession: (id: string, updates: Partial<HandoffSession>) => void;
  activeHandoffId: string | null;
  setActiveHandoffId: (id: string | null) => void;

  // Swarm
  swarmAgents: SwarmAgent[];
  setSwarmAgents: (agents: SwarmAgent[]) => void;
  swarmSessions: AgentSession[];
  addSwarmSession: (s: AgentSession) => void;
  updateSwarmSession: (id: string, updates: Partial<AgentSession>) => void;

  // Server
  serverStatus: ServerStatus;
  setServerStatus: (s: Partial<ServerStatus>) => void;

  // Settings
  serverUrl: string;
  setServerUrl: (url: string) => void;
  theme: 'dark' | 'light';
  setTheme: (t: 'dark' | 'light') => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Navigation
  activeTab: 'dashboard',
  setActiveTab: (tab) => set({ activeTab: tab }),

  // API Keys
  apiKeys: [],
  addApiKey: (key, model) => {
    const provider = detectProvider(key);
    if (!provider) return;
    const newKey: APIKey = {
      id: crypto.randomUUID(),
      provider: provider.id,
      keyPreview: maskKey(key),
      addedAt: new Date().toISOString(),
      isValid: true,
      model: model || provider.models[0],
    };
    set((state) => ({
      apiKeys: [...state.apiKeys, newKey],
      activeProvider: provider.id,
      activeModel: model || provider.models[0],
    }));
  },
  removeApiKey: (id) => set((state) => ({
    apiKeys: state.apiKeys.filter((k) => k.id !== id),
  })),
  activeProvider: null,
  activeModel: null,

  // Chat
  chatMessages: [],
  addChatMessage: (msg) => {
    const newMsg: ChatMessage = {
      ...msg,
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
    };
    set((state) => ({
      chatMessages: [...state.chatMessages, newMsg],
    }));
  },
  isProcessing: false,
  setIsProcessing: (v) => set({ isProcessing: v }),

  // Browser
  browserState: { url: '', title: '', isLoading: false },
  setBrowserState: (s) => set((state) => ({
    browserState: { ...state.browserState, ...s },
  })),

  // Handoff
  handoffSessions: [],
  addHandoffSession: (s) => set((state) => ({
    handoffSessions: [s, ...state.handoffSessions],
  })),
  updateHandoffSession: (id, updates) => set((state) => ({
    handoffSessions: state.handoffSessions.map((s) =>
      s.id === id ? { ...s, ...updates } : s
    ),
  })),
  activeHandoffId: null,
  setActiveHandoffId: (id) => set({ activeHandoffId: id }),

  // Swarm
  swarmAgents: [
    { key: 'news_hound', name: 'News Hound', expertise: 'Current Events', sources: ['Reuters', 'BBC', 'CNN'], depth: 'quick', status: 'idle', priority: 8 },
    { key: 'deep_researcher', name: 'Deep Researcher', expertise: 'Academic/Technical', sources: ['Google Scholar', 'arXiv'], depth: 'thorough', status: 'idle', priority: 5 },
    { key: 'price_checker', name: 'Price Checker', expertise: 'Commerce/Pricing', sources: ['Amazon', 'Flipkart'], depth: 'quick', status: 'idle', priority: 9 },
    { key: 'tech_scanner', name: 'Tech Scanner', expertise: 'Technology/Software', sources: ['GitHub', 'StackOverflow'], depth: 'medium', status: 'idle', priority: 7 },
    { key: 'generalist', name: 'Generalist', expertise: 'General Knowledge', sources: ['Wikipedia', 'Reuters'], depth: 'medium', status: 'idle', priority: 1 },
  ],
  setSwarmAgents: (agents) => set({ swarmAgents: agents }),
  swarmSessions: [],
  addSwarmSession: (s) => set((state) => ({
    swarmSessions: [s, ...state.swarmSessions],
  })),
  updateSwarmSession: (id, updates) => set((state) => ({
    swarmSessions: state.swarmSessions.map((s) =>
      s.id === id ? { ...s, ...updates } : s
    ),
  })),

  // Server
  serverStatus: { online: false, url: 'http://localhost:8001' },
  setServerStatus: (s) => set((state) => ({
    serverStatus: { ...state.serverStatus, ...s },
  })),

  // Settings
  serverUrl: 'http://localhost:8001',
  setServerUrl: (url) => set({ serverUrl: url }),
  theme: 'dark',
  setTheme: (t) => set({ theme: t }),
}));
