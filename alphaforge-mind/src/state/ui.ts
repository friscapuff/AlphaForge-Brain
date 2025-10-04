import { create } from 'zustand';

export interface UISlice {
  slowNoticeShown: boolean;
  showSlowNotice: () => void;
  resetSlowNotice: () => void;
  dismissSlowNotice: () => void;
}

export const useUIStore = create<UISlice>((set) => ({
  slowNoticeShown: false,
  showSlowNotice: () => set({ slowNoticeShown: true }),
  resetSlowNotice: () => set({ slowNoticeShown: false }),
  dismissSlowNotice: () => set({ slowNoticeShown: false }),
}));
