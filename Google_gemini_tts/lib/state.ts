/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import { create } from 'zustand';
import { customerSupportTools } from './tools/customer-support';
import { personalAssistantTools } from './tools/personal-assistant';
import { navigationSystemTools } from './tools/navigation-system';

export type Template = 'customer-support' | 'personal-assistant' | 'navigation-system';

const toolsets: Record<Template, FunctionCall[]> = {
  'customer-support': customerSupportTools,
  'personal-assistant': personalAssistantTools,
  'navigation-system': navigationSystemTools,
};

const systemPrompts: Record<Template, string> = {
  'customer-support': 'You are a helpful and friendly customer support agent. Be conversational and concise.',
  'personal-assistant': 'You are a helpful and friendly personal assistant. Be proactive and efficient.',
  'navigation-system': 'You are a helpful and friendly navigation assistant. Provide clear and accurate directions.',
};
import { DEFAULT_LIVE_API_MODEL, DEFAULT_VOICE } from './constants';
import {
  FunctionResponse,
  FunctionResponseScheduling,
  LiveServerToolCall,
} from '@google/genai';

/**
 * Settings
 */

// Load system prompt from the markdown file
const loadSystemPrompt = () => {
  try {
    // Try to load from localStorage first
    const stored = localStorage.getItem('systemPrompt');
    if (stored) {
      return stored;
    }
  } catch (e) {
    console.warn('Failed to load system prompt from localStorage:', e);
  }

  // Default system prompt (this will be replaced by the one loaded from file in the component)
  return `You are a helpful and friendly AI assistant. Be conversational and concise.`;
};

// Load settings from localStorage
const loadSetting = (key: string, defaultValue: any) => {
  try {
    const stored = localStorage.getItem(key);
    if (stored !== null) {
      return JSON.parse(stored);
    }
  } catch (e) {
    console.warn(`Failed to load ${key} from localStorage:`, e);
  }
  return defaultValue;
};

export const useSettings = create<{
  systemPrompt: string;
  model: string;
  voice: string;
  randomVoice: boolean;
  thinkingMode: boolean;
  showThoughts: boolean;
  difficulty: string; // "random" or "1" through "10"
  turnCoverage: string; // "TURN_INCLUDES_ONLY_ACTIVITY" or "TURN_INCLUDES_ALL_INPUT"
  affectiveDialogue: boolean;
  proactiveAudio: boolean;
  setSystemPrompt: (prompt: string) => void;
  setModel: (model: string) => void;
  setVoice: (voice: string) => void;
  setRandomVoice: (random: boolean) => void;
  setThinkingMode: (enabled: boolean) => void;
  setShowThoughts: (show: boolean) => void;
  setDifficulty: (difficulty: string) => void;
  setTurnCoverage: (coverage: string) => void;
  setAffectiveDialogue: (enabled: boolean) => void;
  setProactiveAudio: (enabled: boolean) => void;
}>(set => ({
  systemPrompt: loadSystemPrompt(),
  model: DEFAULT_LIVE_API_MODEL,
  voice: loadSetting('voice', DEFAULT_VOICE),
  randomVoice: loadSetting('voice', DEFAULT_VOICE) === 'RANDOM',
  thinkingMode: loadSetting('thinkingMode', false),
  showThoughts: loadSetting('showThoughts', false),
  difficulty: loadSetting('difficulty', 'random'),
  turnCoverage: loadSetting('turnCoverage', 'TURN_INCLUDES_ONLY_ACTIVITY'),
  affectiveDialogue: loadSetting('affectiveDialogue', false),
  proactiveAudio: loadSetting('proactiveAudio', false),
  setSystemPrompt: prompt => {
    // Save to localStorage when changed
    try {
      localStorage.setItem('systemPrompt', prompt);
    } catch (e) {
      console.warn('Failed to save system prompt to localStorage:', e);
    }
    set({ systemPrompt: prompt });
  },
  setModel: model => set({ model }),
  setVoice: voice => {
    try {
      localStorage.setItem('voice', JSON.stringify(voice));
    } catch (e) {
      console.warn('Failed to save voice to localStorage:', e);
    }
    set({ voice });
  },
  setRandomVoice: random => {
    try {
      localStorage.setItem('randomVoice', JSON.stringify(random));
    } catch (e) {
      console.warn('Failed to save randomVoice to localStorage:', e);
    }
    set({ randomVoice: random });
  },
  setThinkingMode: enabled => {
    try {
      localStorage.setItem('thinkingMode', JSON.stringify(enabled));
    } catch (e) {
      console.warn('Failed to save thinkingMode to localStorage:', e);
    }
    set({ thinkingMode: enabled });
  },
  setShowThoughts: show => {
    try {
      localStorage.setItem('showThoughts', JSON.stringify(show));
    } catch (e) {
      console.warn('Failed to save showThoughts to localStorage:', e);
    }
    set({ showThoughts: show });
  },
  setDifficulty: difficulty => {
    try {
      localStorage.setItem('difficulty', JSON.stringify(difficulty));
    } catch (e) {
      console.warn('Failed to save difficulty to localStorage:', e);
    }
    set({ difficulty });
  },
  setTurnCoverage: coverage => {
    try {
      localStorage.setItem('turnCoverage', JSON.stringify(coverage));
    } catch (e) {
      console.warn('Failed to save turnCoverage to localStorage:', e);
    }
    set({ turnCoverage: coverage });
  },
  setAffectiveDialogue: enabled => {
    try {
      localStorage.setItem('affectiveDialogue', JSON.stringify(enabled));
    } catch (e) {
      console.warn('Failed to save affectiveDialogue to localStorage:', e);
    }
    set({ affectiveDialogue: enabled });
  },
  setProactiveAudio: enabled => {
    try {
      localStorage.setItem('proactiveAudio', JSON.stringify(enabled));
    } catch (e) {
      console.warn('Failed to save proactiveAudio to localStorage:', e);
    }
    set({ proactiveAudio: enabled });
  },
}));

/**
 * UI
 */
export const useUI = create<{
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
}>(set => ({
  isSidebarOpen: true,
  toggleSidebar: () => set(state => ({ isSidebarOpen: !state.isSidebarOpen })),
}));

/**
 * Tools
 */
export interface FunctionCall {
  name: string;
  description?: string;
  parameters?: any;
  isEnabled: boolean;
  scheduling?: FunctionResponseScheduling;
}



export const useTools = create<{
  tools: FunctionCall[];
  template: Template;
  setTemplate: (template: Template) => void;
  toggleTool: (toolName: string) => void;
  addTool: () => void;
  removeTool: (toolName: string) => void;
  updateTool: (oldName: string, updatedTool: FunctionCall) => void;
}>(set => ({
  tools: [],
  template: 'customer-support',
  setTemplate: (template: Template) => {
    set({ tools: toolsets[template], template });
    useSettings.getState().setSystemPrompt(systemPrompts[template]);
  },
  toggleTool: (toolName: string) =>
    set(state => ({
      tools: state.tools.map(tool =>
        tool.name === toolName ? { ...tool, isEnabled: !tool.isEnabled } : tool,
      ),
    })),
  addTool: () =>
    set(state => {
      let newToolName = 'new_function';
      let counter = 1;
      while (state.tools.some(tool => tool.name === newToolName)) {
        newToolName = `new_function_${counter++}`;
      }
      return {
        tools: [
          ...state.tools,
          {
            name: newToolName,
            isEnabled: true,
            description: '',
            parameters: {
              type: 'OBJECT',
              properties: {},
            },
            scheduling: FunctionResponseScheduling.INTERRUPT,
          },
        ],
      };
    }),
  removeTool: (toolName: string) =>
    set(state => ({
      tools: state.tools.filter(tool => tool.name !== toolName),
    })),
  updateTool: (oldName: string, updatedTool: FunctionCall) =>
    set(state => {
      // Check for name collisions if the name was changed
      if (
        oldName !== updatedTool.name &&
        state.tools.some(tool => tool.name === updatedTool.name)
      ) {
        console.warn(`Tool with name "${updatedTool.name}" already exists.`);
        // Prevent the update by returning the current state
        return state;
      }
      return {
        tools: state.tools.map(tool =>
          tool.name === oldName ? updatedTool : tool,
        ),
      };
    }),
}));

/**
 * Logs
 */
export interface LiveClientToolResponse {
  functionResponses?: FunctionResponse[];
}
export interface GroundingChunk {
  web?: {
    uri: string;
    title: string;
  };
}

export interface ConversationTurn {
  timestamp: Date;
  role: 'user' | 'agent' | 'system';
  text: string;
  isFinal: boolean;
  thoughts?: string;
  toolUseRequest?: LiveServerToolCall;
  toolUseResponse?: LiveClientToolResponse;
  groundingChunks?: GroundingChunk[];
}

export const useLogStore = create<{
  turns: ConversationTurn[];
  addTurn: (turn: Omit<ConversationTurn, 'timestamp'>) => void;
  updateLastTurn: (update: Partial<ConversationTurn>) => void;
  clearTurns: () => void;
}>((set, get) => ({
  turns: [],
  addTurn: (turn: Omit<ConversationTurn, 'timestamp'>) =>
    set(state => ({
      turns: [...state.turns, { ...turn, timestamp: new Date() }],
    })),
  updateLastTurn: (update: Partial<Omit<ConversationTurn, 'timestamp'>>) => {
    set(state => {
      if (state.turns.length === 0) {
        return state;
      }
      const newTurns = [...state.turns];
      const lastTurn = { ...newTurns[newTurns.length - 1], ...update };
      newTurns[newTurns.length - 1] = lastTurn;
      return { turns: newTurns };
    });
  },
  clearTurns: () => set({ turns: [] }),
}));
