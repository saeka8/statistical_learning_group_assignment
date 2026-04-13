import type { UploadStatus } from '../../types';
import styles from './StatusIndicator.module.css';

interface StatusIndicatorProps {
  status: UploadStatus;
  label?: string;
}

const statusMap: Record<UploadStatus, { label: string; className: string }> = {
  idle: { label: 'Ready', className: 'idle' },
  uploading: { label: 'Uploading…', className: 'uploading' },
  processing: { label: 'Processing…', className: 'processing' },
  classified: { label: 'Classified', className: 'classified' },
  extracted: { label: 'Extracted', className: 'extracted' },
  error: { label: 'Error', className: 'error' },
};

export function StatusIndicator({ status, label }: StatusIndicatorProps) {
  const config = statusMap[status];
  return (
    <span className={`${styles.indicator} ${styles[config.className]}`}>
      <span className={styles.dot} aria-hidden="true" />
      <span className={styles.label}>{label ?? config.label}</span>
    </span>
  );
}
