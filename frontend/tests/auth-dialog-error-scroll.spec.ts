import { expect, test } from '@playwright/test';

test.use({
  viewport: { width: 1280, height: 640 },
});

test('auth dialog can scroll after a signup error expands the form', async ({ page }) => {
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
  await expect(dialog).toBeVisible();

  await page.getByLabel('Display name').fill('vako');
  await page.getByLabel('Username').fill('V4KO');
  await page.getByLabel('Email address').fill('not-an-email');
  await page.getByLabel('Password').fill('short');

  await dialog.locator('form button[type="submit"]').click();

  await expect(dialog.getByText('Enter a valid email address.')).toBeVisible();
  await expect(dialog.getByText('Ensure this field has at least 8 characters.')).toBeVisible();

  const dialogBox = await dialog.boundingBox();
  const buttonBeforeScroll = await dialog.locator('form button[type="submit"]').boundingBox();
  const before = await dialog.evaluate((node) => ({
    scrollTop: node.scrollTop,
    scrollHeight: node.scrollHeight,
    clientHeight: node.clientHeight,
  }));

  expect(dialogBox).not.toBeNull();
  expect(buttonBeforeScroll).not.toBeNull();
  expect(before.scrollHeight).toBeGreaterThan(before.clientHeight);
  expect(buttonBeforeScroll!.y + buttonBeforeScroll!.height).toBeGreaterThan(
    dialogBox!.y + dialogBox!.height
  );

  await dialog.hover();
  await page.mouse.wheel(0, 1200);

  await expect
    .poll(async () => dialog.evaluate((node) => node.scrollTop), {
      message: 'expected the auth dialog to keep scrolling after the error banner appears',
    })
    .toBeGreaterThan(before.scrollTop);
  const buttonAfterScroll = await dialog.locator('form button[type="submit"]').boundingBox();

  expect(buttonAfterScroll).not.toBeNull();
  expect(buttonAfterScroll!.y + buttonAfterScroll!.height).toBeLessThanOrEqual(
    dialogBox!.y + dialogBox!.height
  );
});
