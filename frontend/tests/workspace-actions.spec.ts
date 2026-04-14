import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('auth_access', 'workspace-access');
    localStorage.setItem('auth_refresh', 'workspace-refresh');
  });

  await page.route('**/api/profile/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          id: 3,
          username: 'vako',
          email: 'vako@example.com',
          profile: {
            display_name: 'Vako',
            avatar_url: '',
            created_at: '2026-04-14T11:00:00Z',
          },
        },
      }),
    });
  });

  await page.route('**/api/workspace/summary/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          totals: {
            uploads: 1,
            processed: 1,
            errors: 0,
            invoices: 1,
          },
          dominant_label: { value: 'invoice', count: 1 },
          recent_invoice_total: '205.50',
          recent_activity: [],
        },
      }),
    });
  });

  await page.route('**/api/documents/?**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 'c0f4e5c4-2a2f-4544-9cd7-3a69a4158f11',
              filename: 'invoice-b.pdf',
              content_type: 'application/pdf',
              file_size: 1200,
              status: 'done',
              label: 'invoice',
              confidence: 0.97,
              created_at: '2026-04-14T12:00:00Z',
              updated_at: '2026-04-14T12:05:00Z',
            },
          ],
        },
      }),
    });
  });

  await page.route('**/api/documents/c0f4e5c4-2a2f-4544-9cd7-3a69a4158f11/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          id: 'c0f4e5c4-2a2f-4544-9cd7-3a69a4158f11',
          filename: 'invoice-b.pdf',
          content_type: 'application/pdf',
          file_size: 1200,
          status: 'done',
          created_at: '2026-04-14T12:00:00Z',
          updated_at: '2026-04-14T12:05:00Z',
          classification: {
            predicted_label: 'invoice',
            confidence: 0.97,
            all_scores: { invoice: 0.97 },
            model_version: 'test-model',
            classified_at: '2026-04-14T12:05:00Z',
          },
          invoice_data: null,
        },
      }),
    });
  });
});

test('workspace actions surface specific backend errors', async ({ page }) => {
  await page.route('**/api/documents/c0f4e5c4-2a2f-4544-9cd7-3a69a4158f11/classify/', async (route) => {
    await route.fulfill({
      status: 422,
      contentType: 'application/json',
      body: JSON.stringify({
        error: {
          code: 'UNPROCESSABLE',
          message: 'Document is already being processed.',
          field_errors: {},
        },
      }),
    });
  });

  await page.route('**/api/documents/c0f4e5c4-2a2f-4544-9cd7-3a69a4158f11/download/', async (route) => {
    await route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({
        error: {
          code: 'NOT_FOUND',
          message: 'Document not found.',
          field_errors: {},
        },
      }),
    });
  });

  await page.goto('/workspace');

  await page.getByRole('button', { name: /re-run analysis/i }).click();
  await expect(page.getByRole('alert')).toContainText('This document is already being processed.');

  await page.getByRole('button', { name: /^download$/i }).click();
  await expect(page.getByRole('alert')).toContainText('We could not download that document.');
});

test('home upload surfaces a specific unsupported-type error', async ({ page }) => {
  await page.route('**/api/documents/', async (route) => {
    await route.fulfill({
      status: 415,
      contentType: 'application/json',
      body: JSON.stringify({
        error: {
          code: 'UNSUPPORTED_MEDIA_TYPE',
          message: "File type 'image/gif' is not supported.",
          field_errors: {},
        },
      }),
    });
  });

  await page.goto('/');

  const uploadArea = page.getByRole('button', {
    name: /upload documents by drag and drop, click to browse, or paste when focused/i,
  });

  await uploadArea.evaluate((element) => {
    const input = element.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['gif'], 'unsupported.gif', { type: 'image/gif' });
    const data = new DataTransfer();
    data.items.add(file);
    input.files = data.files;
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });

  await page.getByRole('button', { name: /analyze all/i }).click();
  await expect(
    page.getByText(/supported document types are pdf, png, jpg, jpeg, and txt/i)
  ).toBeVisible();
});
