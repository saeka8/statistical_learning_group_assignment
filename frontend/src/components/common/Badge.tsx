import styles from './Badge.module.css';

interface BadgeProps {
  label: string;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'accent';
  size?: 'sm' | 'md';
  dot?: boolean;
}

export function Badge({ label, variant = 'default', size = 'sm', dot = false }: BadgeProps) {
  return (
    <span className={`${styles.badge} ${styles[variant]} ${styles[size]}`}>
      {dot && <span className={styles.dot} aria-hidden="true" />}
      {label}
    </span>
  );
}
