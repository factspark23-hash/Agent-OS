export interface Provider {
  id: string;
  name: string;
  keyPrefix: string;
  baseUrl: string;
  models: string[];
  icon: string;
  color: string;
}

export interface APIKey {
  id: string;
  provider: string;
  keyPreview: string;
  addedAt: string;
  isValid: boolean;
  lastValidated?: string;
  model?: string;
}

export interface HandoffSession {
  id: string;
  url: string;
  domain: string;
  status: 'active' | 'completed' | 'cancelled';
  startedAt: string;
  completedAt?: string;
  loginType: 'login' | 'signup' | 'unknown';
}

export interface BrowserState {
  url: string;
  title: string;
  screenshot?: string;
  isLoading: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  reasoning?: string;
  timestamp: string;
  provider?: string;
  model?: string;
}

export interface AgentSession {
  id: string;
  query: string;
  status: 'routing' | 'searching' | 'aggregating' | 'completed' | 'failed';
  agents: string[];
  resultsCount: number;
  startedAt: string;
  completedAt?: string;
}

export interface SwarmAgent {
  key: string;
  name: string;
  expertise: string;
  sources: string[];
  depth: string;
  status: 'idle' | 'searching' | 'completed' | 'failed';
  priority: number;
}

export interface ServerStatus {
  online: boolean;
  url: string;
  version?: string;
  uptime?: number;
  swarmEnabled?: boolean;
  activeSessions?: number;
}

export type TabId = 'dashboard' | 'command' | 'apikeys' | 'browser' | 'handoff' | 'swarm' | 'settings';
