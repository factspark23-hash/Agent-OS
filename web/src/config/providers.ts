import type { Provider } from '../types';

export const PROVIDERS: Provider[] = [
  {
    id: 'openai',
    name: 'OpenAI',
    keyPrefix: 'sk-',
    baseUrl: 'https://api.openai.com/v1',
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
    icon: '🤖',
    color: '#10a37f',
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    keyPrefix: 'sk-ant-',
    baseUrl: 'https://api.anthropic.com/v1',
    models: ['claude-sonnet-4-20250514', 'claude-3-5-sonnet-20241022', 'claude-3-haiku-20240307'],
    icon: '🧠',
    color: '#d4a574',
  },
  {
    id: 'google',
    name: 'Google Gemini',
    keyPrefix: 'AIza',
    baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
    models: ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'],
    icon: '✨',
    color: '#4285f4',
  },
  {
    id: 'xai',
    name: 'xAI (Grok)',
    keyPrefix: 'xai-',
    baseUrl: 'https://api.x.ai/v1',
    models: ['grok-3', 'grok-3-mini', 'grok-2'],
    icon: '⚡',
    color: '#1d9bf0',
  },
  {
    id: 'mistral',
    name: 'Mistral AI',
    keyPrefix: 'mist-',
    baseUrl: 'https://api.mistral.ai/v1',
    models: ['mistral-large-latest', 'mistral-medium-latest', 'mistral-small-latest'],
    icon: '🌊',
    color: '#ff7000',
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    keyPrefix: 'deepseek-',
    baseUrl: 'https://api.deepseek.com/v1',
    models: ['deepseek-chat', 'deepseek-reasoner'],
    icon: '🔍',
    color: '#4a9eff',
  },
  {
    id: 'local',
    name: 'Local / Self-hosted',
    keyPrefix: 'http://',
    baseUrl: 'http://localhost:8080/v1',
    models: [],
    icon: '🏠',
    color: '#6366f1',
  },
];

export function detectProvider(apiKey: string): Provider | null {
  if (!apiKey || apiKey.trim().length === 0) return null;

  // Check by URL prefix first (for local/self-hosted providers)
  if (apiKey.startsWith('http://localhost:') || apiKey.startsWith('http://127.0.0.1:')) {
    return PROVIDERS.find(p => p.id === 'local') || null;
  }

  // Check by key prefix
  for (const provider of PROVIDERS) {
    if (provider.id === 'local') continue;
    if (apiKey.startsWith(provider.keyPrefix)) {
      return provider;
    }
  }

  return null;
}

export function maskKey(key: string): string {
  if (key.startsWith('http')) return key; // Local provider URL
  if (key.length <= 8) return '••••••••';
  return key.slice(0, 4) + '••••' + key.slice(-4);
}

export function validateKeyFormat(apiKey: string, provider: Provider): { valid: boolean; message: string } {
  if (provider.id === 'local') {
    try {
      new URL(apiKey);
      return { valid: true, message: 'Valid local provider URL' };
    } catch {
      return { valid: false, message: 'Invalid URL format' };
    }
  }

  if (!apiKey.startsWith(provider.keyPrefix)) {
    return { valid: false, message: `Key must start with "${provider.keyPrefix}"` };
  }

  const minLength = provider.id === 'google' ? 30 : 20;
  if (apiKey.length < minLength) {
    return { valid: false, message: `Key seems too short (min ${minLength} chars)` };
  }

  return { valid: true, message: 'Key format looks valid' };
}
