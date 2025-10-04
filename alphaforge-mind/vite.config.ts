import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// T004: Vitest configuration embedded here (alternative separate vitest.config.ts)
// Provides jsdom environment & setup file.

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    globals: true,
    exclude: ['tests/visual/**', 'node_modules/**'],
    coverage: {
      reporter: ['text', 'lcov'],
    },
  },
  server: {
    port: 5173,
    open: false,
  },
  build: {
    sourcemap: true,
  },
});
