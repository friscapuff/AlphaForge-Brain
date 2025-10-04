import { create } from 'zustand';
import type { ErrorDescriptor } from '../errors/errorMessages.js';

export interface ActiveErrorState {
  descriptor: ErrorDescriptor;
  correlationId?: string;
  rateLimitResetMs?: number; // epoch ms when rate limit resets
  retryable?: boolean;
  rawDetail?: string;
}

interface ErrorStore {
  current?: ActiveErrorState;
  setError: (err: ActiveErrorState | undefined) => void;
  clear: () => void;
}

export const useErrorStore = create<ErrorStore>()((set) => ({
  current: undefined,
  setError: (err) => set({ current: err }),
  clear: () => set({ current: undefined }),
}));
