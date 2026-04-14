import { expect, test } from '@playwright/test';

test('guests are redirected away from the workspace route', async ({ page }) => {
  await page.goto('/workspace');

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('button', { name: /^log in$/i })).toBeVisible();
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
