import { api } from './api';
import { getDocument, type DocumentResult } from './documents';
import type { WorkspaceSummary } from '../types';

export type WorkspaceDocumentOrdering = 'newest' | 'oldest' | 'confidence';
export type WorkspaceDocumentStatusFilter = 'all' | 'pending' | 'processing' | 'done' | 'error';
export type WorkspaceDocumentLabelFilter = string;

export interface WorkspaceFilters {
  query: string;
  status: WorkspaceDocumentStatusFilter;
  label: WorkspaceDocumentLabelFilter;
  ordering: WorkspaceDocumentOrdering;
}

interface BackendWorkspaceSummary {
  totals: {
    uploads: number;
    processed: number;
    errors: number;
    invoices: number;
  } | null;
  dominant_label: {
    value: string;
    count: number;
  } | null;
  recent_invoice_total: string | null;
  recent_activity: Array<{
    id: string;
    filename: string;
    status: 'pending' | 'processing' | 'done' | 'error';
    label: string | null;
    confidence?: number | null;
    created_at: string;
  }> | null;
}

interface BackendDocumentListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results?: Array<{
    id: string;
    filename: string;
    content_type: string;
    file_size: number;
    status: 'pending' | 'processing' | 'done' | 'error';
    created_at: string;
    updated_at?: string;
    label?: string | null;
    confidence?: number | null;
    classification: unknown;
    invoice_data: unknown;
  }>;
}

function emptySummary(): WorkspaceSummary {
  return {
    totals: {
      uploads: 0,
      processed: 0,
      errors: 0,
      invoices: 0,
    },
    dominantLabel: null,
    recentInvoiceTotal: null,
    recentActivity: [],
  };
}

function mapSummary(summary?: Partial<BackendWorkspaceSummary> | null): WorkspaceSummary {
  const safeSummary = summary ?? {};

  return {
    totals: safeSummary.totals ?? emptySummary().totals,
    dominantLabel: safeSummary.dominant_label
      ? {
          value: safeSummary.dominant_label.value,
          count: safeSummary.dominant_label.count,
        }
      : null,
    recentInvoiceTotal: safeSummary.recent_invoice_total ?? null,
    recentActivity: (safeSummary.recent_activity ?? []).map((item) => ({
      id: item.id,
      filename: item.filename,
      status: item.status,
      label: item.label,
      confidence: item.confidence,
      createdAt: item.created_at,
    })),
  };
}

function buildDocumentsPath(filters: WorkspaceFilters): string {
  const params = new URLSearchParams();
  const query = filters.query.trim();
  if (query) params.set('q', query);
  if (filters.status !== 'all') params.set('status', filters.status);
  if (filters.label !== 'all') params.set('label', filters.label);
  params.set('ordering', filters.ordering);
  return `/documents/?${params.toString()}`;
}

export async function getWorkspaceSummary(): Promise<WorkspaceSummary> {
  const summary = await api.get<
    BackendWorkspaceSummary | { summary?: Partial<BackendWorkspaceSummary> } | Record<string, unknown>
  >('/workspace/summary/');

  if ('totals' in summary || 'recent_activity' in summary || 'dominant_label' in summary) {
    return mapSummary(summary as Partial<BackendWorkspaceSummary>);
  }

  if ('summary' in summary) {
    return mapSummary((summary as { summary?: Partial<BackendWorkspaceSummary> }).summary);
  }

  return emptySummary();
}

export async function listWorkspaceDocuments(filters: WorkspaceFilters): Promise<DocumentResult[]> {
  const response = await api.get<BackendDocumentListResponse>(buildDocumentsPath(filters));
  return (response.results ?? []).map((document) => ({
    backendId: document.id,
    filename: document.filename,
    contentType: document.content_type,
    fileSize: document.file_size,
    status: document.status,
    createdAt: document.created_at,
    updatedAt: document.updated_at ?? document.created_at,
    label: document.label ?? null,
    confidence: document.confidence ?? null,
    classification: undefined,
    extraction: undefined,
  }));
}

export async function getWorkspaceDocument(id: string): Promise<DocumentResult> {
  return getDocument(id);
}
