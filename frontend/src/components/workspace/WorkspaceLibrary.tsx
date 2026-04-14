import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { SectionReveal } from '../common/SectionReveal';
import { formatConfidence, formatFileSize } from '../../utils/helpers';
import type { DocumentResult } from '../../services/documents';
import type { WorkspaceDocumentOrdering, WorkspaceDocumentStatusFilter } from '../../services/workspace';
import styles from './WorkspaceLibrary.module.css';

interface WorkspaceLibraryProps {
  documents: DocumentResult[];
  selectedDocumentId: string | null;
  query: string;
  status: WorkspaceDocumentStatusFilter;
  label: string;
  ordering: WorkspaceDocumentOrdering;
  labelOptions: string[];
  isLoading: boolean;
  onQueryChange: (value: string) => void;
  onStatusChange: (value: WorkspaceDocumentStatusFilter) => void;
  onLabelChange: (value: string) => void;
  onOrderingChange: (value: WorkspaceDocumentOrdering) => void;
  onSelectDocument: (id: string) => void;
}

function formatLabel(value: string): string {
  if (value === 'all') return 'All labels';
  return value
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((token) => token.slice(0, 1).toUpperCase() + token.slice(1))
    .join(' ');
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function WorkspaceLibrary({
  documents,
  selectedDocumentId,
  query,
  status,
  label,
  ordering,
  labelOptions,
  isLoading,
  onQueryChange,
  onStatusChange,
  onLabelChange,
  onOrderingChange,
  onSelectDocument,
}: WorkspaceLibraryProps) {
  const showEmpty = !isLoading && documents.length === 0;

  return (
    <SectionReveal direction="left">
      <section className={styles.library} aria-labelledby="workspace-library-title">
        <div className={styles.header}>
          <div>
            <p className={styles.eyebrow}>Library</p>
            <h2 id="workspace-library-title" className={styles.title}>
              Browse documents
            </h2>
          </div>
          <Badge label={`${documents.length} visible`} variant="accent" />
        </div>

        <Card variant="glass" padding="md" className={styles.filters}>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Search documents</span>
            <input
              type="search"
              className={styles.search}
              placeholder="Search by filename"
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              aria-label="Search documents"
            />
          </label>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>Status</span>
            <select
              className={styles.select}
              value={status}
              onChange={(event) => onStatusChange(event.target.value as WorkspaceDocumentStatusFilter)}
              aria-label="Status"
            >
              <option value="all">All statuses</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="done">Done</option>
              <option value="error">Error</option>
            </select>
          </label>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>Label</span>
            <select
              className={styles.select}
              value={label}
              onChange={(event) => onLabelChange(event.target.value)}
              aria-label="Label"
            >
              <option value="all">All labels</option>
              {labelOptions.map((option) => (
                <option key={option} value={option}>
                  {formatLabel(option)}
                </option>
              ))}
            </select>
          </label>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>Sort by</span>
            <select
              className={styles.select}
              value={ordering}
              onChange={(event) => onOrderingChange(event.target.value as WorkspaceDocumentOrdering)}
              aria-label="Sort by"
            >
              <option value="newest">Newest</option>
              <option value="oldest">Oldest</option>
              <option value="confidence">Confidence</option>
            </select>
          </label>
        </Card>

        {showEmpty ? (
          <Card variant="default" padding="lg" className={styles.emptyState}>
            <h3 className={styles.emptyTitle}>No documents match this view</h3>
            <p className={styles.emptyText}>Adjust your search or filters and try again.</p>
          </Card>
        ) : (
          <Card variant="default" padding="none" className={styles.listCard}>
            {isLoading ? (
              <div className={styles.loadingState} aria-label="Loading documents">
                <div className={styles.loadingRow} />
                <div className={styles.loadingRow} />
                <div className={styles.loadingRow} />
              </div>
            ) : (
              <ul className={styles.list} role="list" aria-label="Documents">
                {documents.map((document) => {
                  const selected = document.backendId === selectedDocumentId;

                  return (
                    <li key={document.backendId} className={styles.item}>
                      <button
                        type="button"
                        className={`${styles.itemButton} ${selected ? styles.itemButtonSelected : ''}`}
                        onClick={() => onSelectDocument(document.backendId)}
                        aria-pressed={selected}
                      >
                        <div className={styles.itemTopline}>
                          <h3 className={styles.filename}>{document.filename}</h3>
                          <Badge label={document.status} variant="default" />
                        </div>
                        <div className={styles.itemMeta}>
                          <span>{formatDate(document.createdAt)}</span>
                          <span>{formatFileSize(document.fileSize)}</span>
                          {typeof document.confidence === 'number' ? (
                            <span>{formatConfidence(document.confidence)}</span>
                          ) : null}
                        </div>
                        <div className={styles.itemFooter}>
                          <span>{document.contentType}</span>
                          <span>{formatLabel(document.label ?? 'unlabeled')}</span>
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </Card>
        )}
      </section>
    </SectionReveal>
  );
}
