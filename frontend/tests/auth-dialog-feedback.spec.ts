import { expect, test } from '@playwright/test';

test('login surfaces the backend invalid-credentials message', async ({ page }) => {
  await page.route('**/api/auth/token/', async (route) => {
    await route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({
        error: {
          code: 'UNAUTHORIZED',
          message: 'No active account found with the given credentials.',
          field_errors: {},
        },
      }),
    });
  });

  await page.goto('/');

  await page.getByRole('button', { name: /^log in$/i }).click();

  const dialog = page.getByRole('dialog', { name: /log in to doclens/i });
  await page.getByLabel('Username').fill('wrong-user');
  await page.getByLabel('Password').fill('wrong-password');
  await dialog.locator('form button[type="submit"]').click();

  await expect(dialog.getByRole('alert')).toContainText(
    'No active account found with the given credentials.'
  );
});

test.use({
  viewport: { width: 1280, height: 640 },
});

test('signup shows field-specific backend errors and keeps close access pinned', async ({
  page,
}) => {
  await page.route('**/api/auth/register/', async (route) => {
    await route.fulfill({
      status: 400,
      contentType: 'application/json',
      body: JSON.stringify({
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Invalid request data.',
          field_errors: {
            email: ['Enter a valid email address.'],
            password: ['Ensure this field has at least 8 characters.'],
          },
        },
      }),
    });
  });

  await page.goto('/');
  await page.getByRole('button', { name: /^sign up$/i }).click();

  const dialog = page.getByRole('dialog', { name: /create your doclens account/i });
  const closeButton = dialog.getByRole('button', { name: /close authentication dialog/i });

  await page.getByLabel('Display name').fill('vako');
  await page.getByLabel('Username').fill('v4ko');
  await page.getByLabel('Email address').fill('not-an-email');
  await page.getByLabel('Password').fill('short');

  await dialog.locator('form button[type="submit"]').click();

  await expect(dialog.getByText('Enter a valid email address.')).toBeVisible();
  await expect(dialog.getByText('Ensure this field has at least 8 characters.')).toBeVisible();

  const dialogBox = await dialog.boundingBox();
  const closeBeforeScroll = await closeButton.boundingBox();
  const beforeScrollTop = await dialog.evaluate((node) => node.scrollTop);

  expect(dialogBox).not.toBeNull();
  expect(closeBeforeScroll).not.toBeNull();
  expect(closeBeforeScroll!.y).toBeLessThanOrEqual(dialogBox!.y + 24);

  await dialog.hover();
  await page.mouse.wheel(0, 1200);

  await expect
    .poll(async () => dialog.evaluate((node) => node.scrollTop), {
      message: 'expected the signup dialog to scroll after backend field errors expand it',
    })
    .toBeGreaterThan(beforeScrollTop);

  const closeAfterScroll = await closeButton.boundingBox();
  expect(closeAfterScroll).not.toBeNull();
  expect(Math.abs(closeAfterScroll!.y - closeBeforeScroll!.y)).toBeLessThanOrEqual(4);
});
