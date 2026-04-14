import { expect, test } from '@playwright/test';

test('pipeline cards replay their reveal when scrolled back into view', async ({ page }) => {
  await page.goto('/');

  const firstStep = page.locator('[data-pipeline-step="input"]');
  await expect(firstStep).toHaveAttribute('data-in-view', 'false');

  await firstStep.scrollIntoViewIfNeeded();
  await expect(firstStep).toHaveAttribute('data-in-view', 'true');

  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
  await expect(firstStep).toHaveAttribute('data-in-view', 'false');

  await firstStep.scrollIntoViewIfNeeded();
  await expect(firstStep).toHaveAttribute('data-in-view', 'true');
});
