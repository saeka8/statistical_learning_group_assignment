import { expect, test } from '@playwright/test';

test('batch analysis exposes document names and lets results switch per document', async ({
  page,
}) => {
  await page.goto('/');

  await expect(page.getByText(/workflow summary/i)).toBeVisible();
  await expect(page.getByText(/demo posture/i)).toHaveCount(0);

  await page.getByRole('button', { name: /nexus_invoice_2025\.pdf/i }).click();
  await page.getByRole('button', { name: /nda_agreement_v3\.pdf/i }).click();

  await page.getByRole('button', { name: /analyze all/i }).click();

  await expect(page.getByRole('heading', { name: /final class decision/i })).toBeVisible({
    timeout: 15000,
  });

  await expect(page.getByText(/analyzed documents/i)).toBeVisible();
  await expect(
    page.getByRole('button', { name: /show results for nexus_invoice_2025\.pdf/i })
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: /show results for nda_agreement_v3\.pdf/i })
  ).toBeVisible();

  await page.getByRole('button', { name: /show results for nda_agreement_v3\.pdf/i }).click();

  const classificationSection = page.getByRole('region', { name: /final class decision/i });

  await expect(
    classificationSection.getByRole('status', { name: /active document nda_agreement_v3\.pdf/i })
  ).toBeVisible();
  await expect(classificationSection.getByRole('heading', { name: /contract/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: /recovered invoice fields/i })).toHaveCount(0);

  await page
    .getByRole('button', { name: /show results for nexus_invoice_2025\.pdf/i })
    .click();

  const extractionSection = page.getByRole('region', { name: /recovered invoice fields/i });

  await expect(
    classificationSection.getByRole('status', {
      name: /active document nexus_invoice_2025\.pdf/i,
    })
  ).toBeVisible();
  await expect(classificationSection.getByRole('heading', { name: /invoice/i })).toBeVisible();
  await expect(extractionSection).toBeVisible();
  await expect(
    extractionSection.getByRole('status', {
      name: /active document nexus_invoice_2025\.pdf/i,
    })
  ).toBeVisible();
});
