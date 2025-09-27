import { vi } from 'vitest';

export interface InstallCanvasOptions { onStroke?: () => void }

/** Installs a lightweight 2D canvas context mock for jsdom tests. Idempotent. */
export function installMockCanvas(opts: InstallCanvasOptions = {}) {
  const proto: any = (HTMLCanvasElement as any).prototype;
  if (proto.getContext && proto.getContext.__isMock) return;
  proto.getContext = vi.fn().mockImplementation(() => {
    const ctx: any = {
      globalAlpha: 1,
      strokeStyle: '#000',
      fillStyle: '#000',
      lineWidth: 1,
      clearRect: () => {}, save: () => {}, restore: () => {}, beginPath: () => {}, moveTo: () => {}, lineTo: () => {}, closePath: () => {}, fill: () => {},
      stroke: () => { opts.onStroke?.(); },
    };
    ctx.__isMockContext = true;
    return ctx;
  });
  proto.getContext.__isMock = true;
}
