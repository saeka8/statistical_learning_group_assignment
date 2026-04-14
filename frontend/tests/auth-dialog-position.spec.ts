import { expect, test } from '@playwright/test';

test('auth dialog stays inside the viewport after opening from a scrolled page', async ({
  page,
}) => {
  await page.goto('/');

  await page.locator('#workspace').scrollIntoViewIfNeeded();

  const nav = page.getByRole('navigation', { name: /main navigation/i });
  await nav.getByRole('button', { name: /^sign up$/i }).click();

  const dialog = page.getByRole('dialog', { name: /create your doclens account/i });
  await expect(dialog).toBeVisible();

  const box = await dialog.boundingBox();
  const viewport = page.viewportSize();

  expect(box).not.toBeNull();
  expect(viewport).not.toBeNull();

  expect(box!.y).toBeGreaterThanOrEqual(0);
  expect(box!.y + box!.height).toBeLessThanOrEqual(viewport!.height);
});
