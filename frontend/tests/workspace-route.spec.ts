import { expect, test } from '@playwright/test';

test('guests are redirected away from the workspace route and can continue after login', async ({
  page,
}) => {
  await page.route('**/api/auth/token/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          access: 'workspace-access-token',
          refresh: 'workspace-refresh-token',
        },
      }),
    });
  });

  await page.route('**/api/profile/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          username: 'ada',
          email: 'ada@example.com',
          profile: {
            display_name: 'Ada Lovelace',
            avatar_url: '',
            created_at: '2026-04-14T00:00:00.000Z',
          },
        },
      }),
    });
  });

  await page.goto('/workspace');

  await expect(page).toHaveURL(/\/$/);

  const dialog = page.getByRole('dialog', { name: /log in to doclens/i });
  await expect(dialog).toBeVisible();

  await dialog.getByLabel(/username/i).fill('ada');
  await dialog.getByLabel(/^password$/i).fill('secret-password');
  await dialog.getByRole('button', { name: /sign in/i }).click();

  await expect(page).toHaveURL(/\/workspace$/);
  await expect(page.getByRole('heading', { name: 'Workspace' })).toBeVisible();
});

test('authenticated users can open the workspace route', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('auth_access', 'workspace-access-token');
    localStorage.setItem('auth_refresh', 'workspace-refresh-token');
  });

  await page.route('**/api/profile/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          username: 'ada',
          email: 'ada@example.com',
          profile: {
            display_name: 'Ada Lovelace',
            avatar_url: '',
            created_at: '2026-04-14T00:00:00.000Z',
          },
        },
      }),
    });
  });

  await page.route('**/api/workspace/summary/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: { documents: [], summary: {} } }),
    });
  });

  await page.route('**/api/documents/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: {} }),
    });
  });

  await page.goto('/workspace');

  await expect(page.getByRole('heading', { name: 'Workspace' })).toBeVisible();
});
