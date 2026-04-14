import { expect, test } from '@playwright/test';

test('brand mark appears in the app shell and favicon remains wired', async ({ page }) => {
  await page.goto('/');

  const brandMarks = page.getByRole('img', { name: /doclens brand mark/i });
  await expect(brandMarks).toHaveCount(2);
  await expect(brandMarks.first()).toBeVisible();
  await expect(brandMarks.nth(1)).toBeVisible();

  await expect(page.locator('link[rel="icon"][href="/favicon.svg"]')).toHaveCount(1);
});
