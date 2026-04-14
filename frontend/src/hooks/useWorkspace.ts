import { useCallback, useEffect, useMemo, useState } from 'react';
import { getWorkspaceDocument, getWorkspaceSummary, listWorkspaceDocuments, type WorkspaceDocumentLabelFilter, type WorkspaceDocumentOrdering, type WorkspaceDocumentStatusFilter } from '../services/workspace';
import type { DocumentResult } from '../services/documents';
import type { WorkspaceSummary } from '../types';

interface WorkspaceState {
  summary: WorkspaceSummary | null;
  documents: DocumentResult[];
  selectedDocumentId: string | null;
  selectedDocument: DocumentResult | null;
  isSummaryLoading: boolean;
  isDocumentsLoading: boolean;
  isDocumentLoading: boolean;
  error: string | null;
  query: string;
  status: WorkspaceDocumentStatusFilter;
  label: WorkspaceDocumentLabelFilter;
  ordering: WorkspaceDocumentOrdering;
  labelOptions: string[];
  setQuery: (query: string) => void;
  setStatus: (status: WorkspaceDocumentStatusFilter) => void;
  setLabel: (label: WorkspaceDocumentLabelFilter) => void;
  setOrdering: (ordering: WorkspaceDocumentOrdering) => void;
  selectDocument: (id: string) => void;
  reload: () => void;
}

function uniqueLabels(documents: DocumentResult[], selectedLabel: string): string[] {
  const labels = new Set<string>();
  documents.forEach((document) => {
    if (document.label) labels.add(document.label);
  });

  if (selectedLabel !== 'all') {
    labels.add(selectedLabel);
  }

  return Array.from(labels).sort((left, right) => left.localeCompare(right));
}

export function useWorkspace(): WorkspaceState {
  const [summary, setSummary] = useState<WorkspaceSummary | null>(null);
  const [documents, setDocuments] = useState<DocumentResult[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<DocumentResult | null>(null);
  const [isSummaryLoading, setIsSummaryLoading] = useState(true);
  const [isDocumentsLoading, setIsDocumentsLoading] = useState(true);
  const [isDocumentLoading, setIsDocumentLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<WorkspaceDocumentStatusFilter>('all');
  const [label, setLabel] = useState<WorkspaceDocumentLabelFilter>('all');
  const [ordering, setOrdering] = useState<WorkspaceDocumentOrdering>('newest');

  const loadSummary = useCallback(() => {
    let alive = true;

    setIsSummaryLoading(true);
    getWorkspaceSummary()
      .then((data) => {
        if (!alive) return;
        setSummary(data);
      })
      .catch(() => {
        if (!alive) return;
        setError('We could not load the workspace summary.');
      })
      .finally(() => {
        if (!alive) return;
        setIsSummaryLoading(false);
      });

    return () => {
      alive = false;
    };
  }, []);

  const loadDocuments = useCallback(() => {
    let alive = true;

    setIsDocumentsLoading(true);
    setError(null);

    listWorkspaceDocuments({ query, status, label, ordering })
      .then((data) => {
        if (!alive) return;
        setDocuments(data);
      })
      .catch(() => {
        if (!alive) return;
        setDocuments([]);
        setError('We could not load your documents.');
      })
      .finally(() => {
        if (!alive) return;
        setIsDocumentsLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [label, ordering, query, status]);

  useEffect(() => loadSummary(), [loadSummary]);
  useEffect(() => loadDocuments(), [loadDocuments]);

  useEffect(() => {
    if (documents.length === 0) {
      setSelectedDocumentId(null);
      setSelectedDocument(null);
      return;
    }

    setSelectedDocumentId((current) => {
      if (current && documents.some((document) => document.backendId === current)) {
        return current;
      }

      return documents[0].backendId;
    });
  }, [documents]);

  useEffect(() => {
    if (!selectedDocumentId) {
      setSelectedDocument(null);
      return;
    }

    let alive = true;
    setIsDocumentLoading(true);

    getWorkspaceDocument(selectedDocumentId)
      .then((data) => {
        if (!alive) return;
        setSelectedDocument(data);
      })
      .catch(() => {
        if (!alive) return;
        setSelectedDocument(null);
        setError('We could not load the selected document.');
      })
      .finally(() => {
        if (!alive) return;
        setIsDocumentLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [selectedDocumentId]);

  const labelOptions = useMemo(() => uniqueLabels(documents, label), [documents, label]);

  return {
    summary,
    documents,
    selectedDocumentId,
    selectedDocument,
    isSummaryLoading,
    isDocumentsLoading,
    isDocumentLoading,
    error,
    query,
    status,
    label,
    ordering,
    labelOptions,
    setQuery,
    setStatus,
    setLabel,
    setOrdering,
    selectDocument: setSelectedDocumentId,
    reload: () => {
      loadSummary();
      loadDocuments();
    },
  };
}
