import { useEffect, useState } from 'react';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import styles from './ConfidenceBar.module.css';

interface ConfidenceBarProps {
  value: number;
  label?: string;
  color?: string;
  showValue?: boolean;
  animate?: boolean;
  size?: 'sm' | 'md' | 'lg';
  highlighted?: boolean;
}

export function ConfidenceBar({
  value,
  label,
  color = 'var(--color-accent-indigo)',
  showValue = true,
  animate = true,
  size = 'md',
  highlighted = false,
}: ConfidenceBarProps) {
  const reducedMotion = usePrefersReducedMotion();
  const [displayWidth, setDisplayWidth] = useState(reducedMotion || !animate ? value * 100 : 0);
  const width = reducedMotion || !animate ? value * 100 : displayWidth;

  useEffect(() => {
    if (reducedMotion || !animate) {
      return;
    }
    const timer = setTimeout(() => setDisplayWidth(value * 100), 100);
    return () => clearTimeout(timer);
  }, [value, animate, reducedMotion]);

  const percentage = `${(value * 100).toFixed(1)}%`;

  return (
    <div className={`${styles.container} ${highlighted ? styles.highlighted : ''}`}>
      {label && (
        <div className={styles.header}>
          <span className={styles.label}>{label}</span>
          {showValue && <span className={styles.value}>{percentage}</span>}
        </div>
      )}
      <div
        className={`${styles.track} ${styles[size]}`}
        role="progressbar"
        aria-valuenow={Math.round(value * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label ? `${label}: ${percentage}` : percentage}
      >
        <div
          className={styles.fill}
          style={{
            width: `${width}%`,
            background: color,
          }}
        />
      </div>
    </div>
  );
}
