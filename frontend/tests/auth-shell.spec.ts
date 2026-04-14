import { expect, test } from '@playwright/test';

test('navbar prioritizes auth entry and supports a preview account state', async ({ page }) => {
  await page.goto('/');

  const nav = page.getByRole('navigation', { name: /main navigation/i });

  await expect(nav.getByRole('link', { name: /workspace/i })).toHaveCount(0);
  await expect(nav.getByRole('link', { name: /method/i })).toHaveCount(0);
  await expect(nav.getByText(/classical ml/i)).toHaveCount(0);

  await expect(nav.getByRole('button', { name: /^log in$/i })).toBeVisible();
  await expect(nav.getByRole('button', { name: /^sign up$/i })).toBeVisible();

  await nav.getByRole('button', { name: /^sign up$/i }).click();

  const dialog = page.getByRole('dialog', { name: /create your doclens account/i });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText(/backend connection lands in the next integration pass/i)).toBeVisible();

  await dialog.getByLabel(/full name/i).fill('Ada Lovelace');
  await dialog.getByLabel(/email address/i).fill('ada@example.com');
  await dialog.getByLabel(/^password$/i).fill('preview-only');
  await dialog.getByRole('button', { name: /continue in preview/i }).click();

  await expect(
    nav.getByRole('button', { name: /open account menu for ada lovelace/i })
  ).toBeVisible();
  await expect(nav.getByRole('button', { name: /^log in$/i })).toHaveCount(0);
  await expect(nav.getByRole('button', { name: /^sign up$/i })).toHaveCount(0);

  await nav.getByRole('button', { name: /open account menu for ada lovelace/i }).click();
  await expect(page.getByText(/saved files sync will appear here once backend is connected/i)).toBeVisible();

  await page.getByRole('button', { name: /sign out/i }).click();

  await expect(nav.getByRole('button', { name: /^log in$/i })).toBeVisible();
  await expect(nav.getByRole('button', { name: /^sign up$/i })).toBeVisible();
});
