/// <reference types="vitest" />
// @playwright-only
// Guard: only execute when RUN_PLAYWRIGHT env set to avoid Vitest collecting this file.
if (!process.env.RUN_PLAYWRIGHT) {
  // Vitest collector sees this file; declare a skipped placeholder suite.
  // @ts-ignore
  describe('visual:chartBaseline (playwright placeholder)', () => { it.skip('skipped – RUN_PLAYWRIGHT not set', () => {}); });
} else {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { test, expect } = require('@playwright/test');

// T056: Placeholder visual regression test.
// For now this only verifies page structure; screenshot step is optional.
// A deterministic baseline screenshot command can be added after CI font/timezone stabilization.

// Skip entirely when running under vitest (unit/integration) environment.
  test.describe('Chart Analysis Visual Smoke', () => {
    test('loads chart analysis page shell', async ({ page }: { page: any }) => {
      try {
        await page.goto('/');
      } catch (err) {
        test.skip(true, 'Dev server not running (vite). Run npm run dev before visual tests.');
      }
      const bodyContent = await page.content();
      expect(bodyContent.length).toBeGreaterThan(0);
      await page.screenshot({ path: 'tests/visual/__screenshots__/chart-analysis-shell.png', fullPage: false });
    });
  });
}
