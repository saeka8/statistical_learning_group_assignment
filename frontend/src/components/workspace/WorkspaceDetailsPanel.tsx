import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { ConfidenceBar } from '../common/ConfidenceBar';
import { SectionReveal } from '../common/SectionReveal';
import { formatConfidence, formatFileSize } from '../../utils/helpers';
import type { DocumentResult } from '../../services/documents';
import styles from './WorkspaceDetailsPanel.module.css';

interface WorkspaceDetailsPanelProps {
  document: DocumentResult | null;
  isLoading: boolean;
}

function formatLabel(value?: string | null): string {
  if (!value) return 'Unlabeled';
  return value
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((token) => token.slice(0, 1).toUpperCase() + token.slice(1))
    .join(' ');
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export function WorkspaceDetailsPanel({
  document,
  isLoading,
}: WorkspaceDetailsPanelProps) {
  return (
    <SectionReveal direction="right">
      <section className={styles.details} aria-labelledby="workspace-details-title">
        <div className={styles.header}>
          <div>
            <p className={styles.eyebrow}>Document details</p>
            <h2 id="workspace-details-title" className={styles.title}>
              Selected document
            </h2>
          </div>
          {document ? <Badge label={document.status} variant="info" /> : null}
        </div>

        {!document ? (
          <Card variant="default" padding="lg" className={styles.emptyState}>
            <h3 className={styles.emptyTitle}>
              {isLoading ? 'Loading document details' : 'No document selected'}
            </h3>
            <p className={styles.emptyText}>
              {isLoading
                ? 'Fetching the latest classification and extraction data.'
                : 'Pick a document from the library to inspect its timestamps, classification, and extracted fields.'}
            </p>
          </Card>
        ) : (
          <div className={styles.stack}>
            <Card variant="elevated" padding="lg" className={styles.summaryCard}>
              <div className={styles.summaryHeader}>
                <div>
                  <h3 className={styles.filename}>{document.filename}</h3>
                  <p className={styles.subtitle}>{document.contentType}</p>
                </div>
                <Badge label={formatLabel(document.label)} variant="accent" />
              </div>


              <div className={styles.metaGrid}>
                <div className={styles.metaBlock}>
                  <span className={styles.metaLabel}>File size</span>
                  <span className={styles.metaValue}>{formatFileSize(document.fileSize)}</span>
                </div>
                <div className={styles.metaBlock}>
                  <span className={styles.metaLabel}>Created</span>
                  <span className={styles.metaValue}>{formatDate(document.createdAt)}</span>
                </div>
                <div className={styles.metaBlock}>
                  <span className={styles.metaLabel}>Updated</span>
                  <span className={styles.metaValue}>{formatDate(document.updatedAt)}</span>
                </div>
                <div className={styles.metaBlock}>
                  <span className={styles.metaLabel}>Confidence</span>
                  <span className={styles.metaValue}>
                    {typeof document.confidence === 'number'
                      ? formatConfidence(document.confidence)
                      : 'N/A'}
                  </span>
                </div>
              </div>
            </Card>

            {document.classification ? (
              <Card variant="default" padding="lg" className={styles.sectionCard}>
                <div className={styles.sectionHeader}>
                  <h3 className={styles.sectionTitle}>Classification</h3>
                  <Badge label={document.classification.predictedLabel} variant="info" />
                </div>

                <div className={styles.classificationMeta}>
                  <span>
                    Top score{' '}
                    {document.classification.scores[0]
                      ? formatConfidence(document.classification.scores[0].confidence)
                      : 'N/A'}
                  </span>
                  <span>Model runtime {document.classification.processingTimeMs} ms</span>
                </div>

                <div className={styles.scoreList}>
                  {document.classification.scores.map((score) => (
                    <ConfidenceBar
                      key={score.category}
                      label={score.label}
                      value={score.confidence}
                      color="var(--color-accent-blue)"
                      size="sm"
                    />
                  ))}
                </div>
              </Card>
            ) : null}

            {document.extraction ? (
              <Card variant="default" padding="lg" className={styles.sectionCard}>
                <div className={styles.sectionHeader}>
                  <h3 className={styles.sectionTitle}>Invoice extraction</h3>
                  <Badge label="invoice" variant="success" />
                </div>

                <div className={styles.fieldGrid}>
                  <div className={styles.field}>
                    <span className={styles.fieldLabel}>Invoice number</span>
                    <span className={styles.fieldValue}>{document.extraction.invoiceNumber.value}</span>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.fieldLabel}>Invoice date</span>
                    <span className={styles.fieldValue}>{document.extraction.invoiceDate.value}</span>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.fieldLabel}>Due date</span>
                    <span className={styles.fieldValue}>{document.extraction.dueDate.value}</span>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.fieldLabel}>Issuer</span>
                    <span className={styles.fieldValue}>{document.extraction.issuerName.value}</span>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.fieldLabel}>Recipient</span>
                    <span className={styles.fieldValue}>{document.extraction.recipientName.value}</span>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.fieldLabel}>Total amount</span>
                    <span className={styles.fieldValue}>{document.extraction.totalAmount.value}</span>
                  </div>
                </div>
              </Card>
            ) : null}
          </div>
        )}
      </section>
    </SectionReveal>
  );
}
