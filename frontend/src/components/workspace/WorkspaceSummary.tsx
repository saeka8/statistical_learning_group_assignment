import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { SectionReveal } from '../common/SectionReveal';
import type { WorkspaceSummary } from '../../types';
import styles from './WorkspaceSummary.module.css';

interface WorkspaceSummaryProps {
  summary: WorkspaceSummary | null;
  isLoading: boolean;
  displayName?: string;
}

function formatLabel(value: string): string {
  return value
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((token) => token.slice(0, 1).toUpperCase() + token.slice(1))
    .join(' ');
}

function formatCount(value: number): string {
  return new Intl.NumberFormat('en-US').format(value);
}

export function WorkspaceSummary({ summary, isLoading, displayName }: WorkspaceSummaryProps) {
  const statCards = summary
    ? [
        { label: 'Total uploads', value: formatCount(summary.totals.uploads) },
        { label: 'Processed', value: formatCount(summary.totals.processed) },
        { label: 'Errors', value: formatCount(summary.totals.errors) },
        { label: 'Invoice files', value: formatCount(summary.totals.invoices) },
      ]
    : [
        { label: 'Total uploads', value: isLoading ? 'Loading' : '0' },
        { label: 'Processed', value: isLoading ? 'Loading' : '0' },
        { label: 'Errors', value: isLoading ? 'Loading' : '0' },
        { label: 'Invoice files', value: isLoading ? 'Loading' : '0' },
      ];

  return (
    <SectionReveal>
      <section className={styles.summary} aria-labelledby="workspace-summary-title">
        <div className={styles.header}>
          <div>
            <p className={styles.eyebrow}>Workspace overview</p>
            <h2 id="workspace-summary-title" className={styles.title}>
              {displayName
                ? `${displayName}'s document pulse`
                : 'A quick pulse on the document library'}
            </h2>
          </div>
          {summary ? (
            <Badge label={`${summary.recentActivity.length} recent items`} variant="info" />
          ) : null}
        </div>

        <div className={styles.grid}>
          <div className={styles.stats}>
            {statCards.map((stat) => (
              <Card key={stat.label} variant="glass" padding="md" className={styles.statCard}>
                <span className={styles.statLabel}>{stat.label}</span>
                <span className={styles.statValue}>{stat.value}</span>
              </Card>
            ))}
          </div>

          <div className={styles.insights}>
            <Card variant="default" padding="md" className={styles.insightCard}>
              <span className={styles.insightLabel}>Most common type</span>
              <span className={styles.insightValue}>
                {summary?.dominantLabel
                  ? formatLabel(summary.dominantLabel.value)
                  : isLoading
                    ? 'Loading'
                    : 'None yet'}
              </span>
              {summary?.dominantLabel ? (
                <p className={styles.insightMeta}>
                  Seen {formatCount(summary.dominantLabel.count)} times in the current library.
                </p>
              ) : null}
            </Card>

            {summary?.recentInvoiceTotal ? (
              <Card variant="accent" padding="md" className={styles.insightCard}>
                <span className={styles.insightLabel}>Recent invoice total</span>
                <span className={styles.insightValue}>EUR {summary.recentInvoiceTotal}</span>
                <p className={styles.insightMeta}>
                  Based on the latest invoice extractions in the dashboard.
                </p>
              </Card>
            ) : null}
          </div>
        </div>

        {summary ? (
          <div className={styles.activity}>
            <div className={styles.activityHeader}>
              <h3 className={styles.activityTitle}>Recent activity</h3>
              <span className={styles.activityMeta}>Latest documents and classifications</span>
            </div>
            {summary.recentActivity.length > 0 ? (
              <ul className={styles.activityList} role="list">
                {summary.recentActivity.map((item) => (
                  <li key={item.id} className={styles.activityItem}>
                    <div>
                      <p className={styles.activityName}>{item.filename}</p>
                      <p className={styles.activitySubline}>
                        {item.label ? formatLabel(item.label) : 'Unlabeled'} -{' '}
                        {new Date(item.createdAt).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </p>
                    </div>
                    <Badge label={item.status} variant="default" />
                  </li>
                ))}
              </ul>
            ) : (
              <Card variant="default" padding="md" className={styles.insightCard}>
                <span className={styles.insightLabel}>Recent activity</span>
                <p className={styles.insightMeta}>
                  New uploads and analysis runs will appear here as your library grows.
                </p>
              </Card>
            )}
          </div>
        ) : null}
      </section>
    </SectionReveal>
  );
}
