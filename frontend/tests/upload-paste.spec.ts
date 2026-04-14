import { expect, test } from '@playwright/test';

async function pasteFile(locator: ReturnType<import('@playwright/test').Page['locator']>, fileName: string) {
  await locator.evaluate((element, name) => {
    const data = new DataTransfer();
    const file = new File(['clipboard-image'], name, { type: 'image/png' });
    data.items.add(file);

    const event = new ClipboardEvent('paste', { bubbles: true, cancelable: true });
    Object.defineProperty(event, 'clipboardData', {
      configurable: true,
      value: data,
    });

    element.dispatchEvent(event);
  }, fileName);
}

test('focused upload area accepts pasted document images', async ({ page }) => {
  await page.goto('/');

  const uploadArea = page.getByRole('button', {
    name: /upload documents by drag and drop, click to browse, or paste when focused/i,
  });

  await uploadArea.focus();
  await pasteFile(uploadArea, 'pasted-doc.png');

  await expect(page.getByText('pasted-doc.png')).toBeVisible();
});

test('pasting outside the focused upload area does not stage a document', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('button', { name: /view methodology/i }).focus();
  await pasteFile(page.locator('body'), 'outside-paste.png');

  await expect(page.getByText('outside-paste.png')).toHaveCount(0);
  await expect(page.getByText('No documents staged yet.')).toBeVisible();
});
