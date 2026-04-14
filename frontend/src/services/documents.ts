import { api } from './api';
import type { ClassificationResult, DocumentCategory, InvoiceExtractionResult } from '../types';

// ── Backend response shapes ───────────────────────────────────────────────────

interface BackendClassification {
  predicted_label: string;
  confidence: number;
  all_scores: Record<string, number>;
  model_version: string;
  classified_at: string;
}

interface BackendInvoiceData {
  invoice_number: string;
  invoice_date: string | null;
  due_date: string | null;
  issuer_name: string;
  recipient_name: string;
  total_amount: string;
  currency: string;
  confidence_map: Record<string, number>;
  extracted_at: string;
}

export interface BackendDocument {
  id: string;
  filename: string;
  content_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'done' | 'error';
  created_at: string;
  classification: BackendClassification | null;
  invoice_data: BackendInvoiceData | null;
}

// ── Mappers ───────────────────────────────────────────────────────────────────

const CATEGORY_META: Record<string, { label: string; icon: string }> = {
  invoice: { label: 'Invoice', icon: 'INV' },
  email: { label: 'Email', icon: 'EML' },
  resume: { label: 'Resume', icon: 'RES' },
  scientific_publication: { label: 'Scientific Publication', icon: 'SCI' },
  unknown: { label: 'Unknown', icon: '???' },
};

function mapClassification(c: BackendClassification): ClassificationResult {
  const scores = Object.entries(c.all_scores)
    .map(([cat, conf]) => ({
      category: cat as DocumentCategory,
      label: CATEGORY_META[cat]?.label ?? cat,
      confidence: conf,
      icon: CATEGORY_META[cat]?.icon ?? '?',
    }))
    .sort((a, b) => b.confidence - a.confidence);

  return {
    predictedCategory: c.predicted_label as DocumentCategory,
    predictedLabel: CATEGORY_META[c.predicted_label]?.label ?? c.predicted_label,
    scores,
    processingTimeMs: 0,
  };
}

function mapExtraction(e: BackendInvoiceData): InvoiceExtractionResult {
  const cm = e.confidence_map ?? {};
  const conf = (key: string) => cm[key] ?? 0.8;
  const amountStr =
    e.total_amount
      ? `${e.currency ? e.currency + ' ' : ''}${e.total_amount}`
      : '';

  return {
    invoiceNumber: { key: 'invoiceNumber', label: 'Invoice Number', value: e.invoice_number ?? '', confidence: conf('invoice_number') },
    invoiceDate: { key: 'invoiceDate', label: 'Invoice Date', value: e.invoice_date ?? '', confidence: conf('invoice_date') },
    dueDate: { key: 'dueDate', label: 'Due Date', value: e.due_date ?? '', confidence: conf('due_date') },
    issuerName: { key: 'issuerName', label: 'Issuer Name', value: e.issuer_name ?? '', confidence: conf('issuer_name') },
    recipientName: { key: 'recipientName', label: 'Recipient Name', value: e.recipient_name ?? '', confidence: conf('recipient_name') },
    totalAmount: { key: 'totalAmount', label: 'Total Amount', value: amountStr, confidence: conf('total_amount') },
  };
}

export interface DocumentResult {
  backendId: string;
  filename: string;
  status: BackendDocument['status'];
  classification: ClassificationResult | undefined;
  extraction: InvoiceExtractionResult | undefined;
}

function mapDocument(d: BackendDocument): DocumentResult {
  return {
    backendId: d.id,
    filename: d.filename,
    status: d.status,
    classification: d.classification ? mapClassification(d.classification) : undefined,
    extraction: d.invoice_data ? mapExtraction(d.invoice_data) : undefined,
  };
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function uploadDocument(file: File): Promise<DocumentResult> {
  const form = new FormData();
  form.append('file', file);
  const doc = await api.postForm<BackendDocument>('/documents/', form);
  return mapDocument(doc);
}

export async function getDocument(id: string): Promise<DocumentResult> {
  const doc = await api.get<BackendDocument>(`/documents/${id}/`);
  return mapDocument(doc);
}

export async function deleteDocument(id: string): Promise<void> {
  await api.del(`/documents/${id}/`);
}

/**
 * Poll a document until its status is 'done' or 'error', calling
 * onUpdate with each intermediate result.
 */
export function pollDocument(
  id: string,
  onUpdate: (result: DocumentResult) => void,
  intervalMs = 2500,
  maxAttempts = 60
): Promise<DocumentResult> {
  return new Promise((resolve, reject) => {
    let attempts = 0;

    const tick = async () => {
      try {
        attempts += 1;
        const result = await getDocument(id);
        onUpdate(result);

        if (result.status === 'done' || result.status === 'error') {
          resolve(result);
          return;
        }

        if (attempts >= maxAttempts) {
          reject(new Error('Analysis timed out.'));
          return;
        }

        setTimeout(tick, intervalMs);
      } catch (err) {
        reject(err);
      }
    };

    // Start polling after the first interval so the backend has time to enqueue
    setTimeout(tick, intervalMs);
  });
}
