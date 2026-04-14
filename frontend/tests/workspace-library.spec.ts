import { expect, test } from '@playwright/test';

const documents = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    filename: 'invoice-q1.pdf',
    content_type: 'application/pdf',
    file_size: 245760,
    status: 'done',
    label: 'invoice',
    confidence: 0.97,
    created_at: '2026-04-14T08:15:00.000Z',
    updated_at: '2026-04-14T08:20:00.000Z',
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    filename: 'resume-final.pdf',
    content_type: 'application/pdf',
    file_size: 98304,
    status: 'error',
    label: 'resume',
    confidence: 0.81,
    created_at: '2026-04-13T13:05:00.000Z',
    updated_at: '2026-04-13T13:07:00.000Z',
  },
  {
    id: '33333333-3333-3333-3333-333333333333',
    filename: 'research-notes.pdf',
    content_type: 'application/pdf',
    file_size: 327680,
    status: 'processing',
    label: 'scientific_publication',
    confidence: 0.64,
    created_at: '2026-04-12T17:45:00.000Z',
    updated_at: '2026-04-12T17:50:00.000Z',
  },
];

test.beforeEach(async ({ page }) => {
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
      body: JSON.stringify({
        data: {
          totals: {
            uploads: 4,
            processed: 2,
            errors: 1,
            invoices: 3,
          },
          dominant_label: {
            value: 'invoice',
            count: 3,
          },
          recent_invoice_total: '205.50',
          recent_activity: documents.map((document) => ({
            id: document.id,
            filename: document.filename,
            status: document.status,
            label: document.label,
            confidence: document.confidence,
            created_at: document.created_at,
          })),
        },
      }),
    });
  });

  await page.route('**/api/documents/?**', async (route) => {
    const url = new URL(route.request().url());
    const query = (url.searchParams.get('q') ?? '').trim().toLowerCase();
    const status = (url.searchParams.get('status') ?? '').trim();
    const label = (url.searchParams.get('label') ?? '').trim();
    const ordering = (url.searchParams.get('ordering') ?? 'newest').trim();

    let results = [...documents];

    if (query) {
      results = results.filter((document) => document.filename.toLowerCase().includes(query));
    }

    if (status) {
      results = results.filter((document) => document.status === status);
    }

    if (label) {
      results = results.filter((document) => document.label === label);
    }

    if (ordering === 'oldest') {
      results = [...results].sort(
        (left, right) => new Date(left.created_at).getTime() - new Date(right.created_at).getTime()
      );
    } else if (ordering === 'confidence') {
      results = [...results].sort((left, right) => (right.confidence ?? 0) - (left.confidence ?? 0));
    } else {
      results = [...results].sort(
        (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
      );
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          count: results.length,
          next: null,
          previous: null,
          results,
        },
      }),
    });
  });

  await page.route('**/api/documents/11111111-1111-1111-1111-111111111111/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          ...documents[0],
          classification: {
            predicted_label: 'invoice',
            confidence: 0.97,
            all_scores: {
              invoice: 0.97,
              resume: 0.02,
              email: 0.01,
            },
            model_version: 'workspace-test-model',
            classified_at: '2026-04-14T08:20:00.000Z',
          },
          invoice_data: {
            invoice_number: 'INV-204',
            invoice_date: '2026-04-10',
            due_date: '2026-04-24',
            issuer_name: 'Lunar Labs',
            recipient_name: 'DocLens',
            total_amount: '205.50',
            currency: 'EUR',
            confidence_map: {
              invoice_number: 0.99,
              issuer_name: 0.94,
              total_amount: 0.96,
            },
            extracted_at: '2026-04-14T08:21:00.000Z',
          },
        },
      }),
    });
  });

  await page.route('**/api/documents/22222222-2222-2222-2222-222222222222/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          ...documents[1],
          classification: {
            predicted_label: 'resume',
            confidence: 0.81,
            all_scores: {
              resume: 0.81,
              invoice: 0.12,
              email: 0.07,
            },
            model_version: 'workspace-test-model',
            classified_at: '2026-04-13T13:06:00.000Z',
          },
          invoice_data: null,
        },
      }),
    });
  });

  await page.route('**/api/documents/33333333-3333-3333-3333-333333333333/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          ...documents[2],
          classification: {
            predicted_label: 'scientific_publication',
            confidence: 0.64,
            all_scores: {
              scientific_publication: 0.64,
              resume: 0.2,
              invoice: 0.16,
            },
            model_version: 'workspace-test-model',
            classified_at: '2026-04-12T17:50:00.000Z',
          },
          invoice_data: null,
        },
      }),
    });
  });
});

test('workspace renders summary stats, auto-selects filtered documents, and updates the details rail', async ({
  page,
}) => {
  await page.goto('/workspace');

  const totalUploadsCard = page.getByText('Total uploads').locator('..');
  const dominantTypeCard = page.getByText('Most common type').locator('..');
  const invoiceTotalCard = page.getByText('Recent invoice total').locator('..');
  const detailsPanel = page.getByRole('region', { name: 'Selected document' });
  const libraryRegion = page.getByRole('region', { name: 'Browse documents' });

  await expect(page.getByRole('heading', { name: 'Workspace' })).toBeVisible();
  await expect(totalUploadsCard).toContainText('Total uploads');
  await expect(totalUploadsCard).toContainText('4');
  await expect(dominantTypeCard).toContainText('Most common type');
  await expect(dominantTypeCard).toContainText('Invoice');
  await expect(invoiceTotalCard).toContainText('Recent invoice total');
  await expect(invoiceTotalCard).toContainText('EUR 205.50');

  await expect(detailsPanel.getByRole('heading', { name: 'invoice-q1.pdf' })).toBeVisible();
  await expect(detailsPanel.getByText('Lunar Labs')).toBeVisible();

  const search = libraryRegion.getByRole('searchbox', { name: /search documents/i });
  await search.fill('resume');

  await expect(libraryRegion.getByRole('listitem')).toHaveCount(1);
  await expect(libraryRegion.getByRole('button', { name: /resume-final\.pdf/i })).toBeVisible();
  await expect(detailsPanel.getByRole('heading', { name: 'resume-final.pdf' })).toBeVisible();

  await search.fill('contract');
  await expect(page.getByText(/no documents match this view/i)).toBeVisible();
  await expect(page.getByText(/adjust your search or filters/i)).toBeVisible();

  await search.fill('');
  await libraryRegion.getByLabel(/status/i).selectOption('processing');

  await expect(libraryRegion.getByRole('button', { name: /research-notes\.pdf/i })).toBeVisible();
  await expect(detailsPanel.getByRole('heading', { name: 'research-notes.pdf' })).toBeVisible();

  await libraryRegion.getByLabel(/status/i).selectOption('all');
  await libraryRegion.getByLabel(/sort by/i).selectOption('oldest');

  await expect(libraryRegion.getByRole('listitem').first()).toContainText('research-notes.pdf');
});
