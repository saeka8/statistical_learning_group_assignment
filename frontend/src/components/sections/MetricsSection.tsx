import { sampleMetrics } from '../../data/sampleData';
import { useIntersectionReveal } from '../../hooks/useIntersectionReveal';
import { AnimatedCounter } from '../common/AnimatedCounter';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { SectionReveal } from '../common/SectionReveal';
import { Container } from '../layout/Container';
import styles from './MetricsSection.module.css';

export function MetricsSection() {
  const { ref, isVisible } = useIntersectionReveal<HTMLDivElement>({ threshold: 0.3 });

  return (
    <section id="metrics" className="section-padding" aria-labelledby="metrics-title">
      <Container>
        <SectionReveal>
          <div className={styles.header}>
            <Badge label="Evaluation Metrics" variant="accent" size="md" />
            <h2 id="metrics-title" className={styles.title}>
              Performance Benchmarks
            </h2>
            <p className={styles.subtitle}>
              Evaluation results on the held-out test set, demonstrating strong classification
              accuracy and extraction completeness across all document categories.
            </p>
          </div>
        </SectionReveal>

        <div className={styles.metricsGrid} ref={ref}>
          {sampleMetrics.map((metric, i) => (
            <SectionReveal key={metric.label} delay={i * 0.1}>
              <Card variant="elevated" padding="lg" hoverable className={styles.metricCard}>
                <div
                  className={styles.metricAccent}
                  style={{ background: metric.color }}
                  aria-hidden="true"
                />
                <p className={styles.metricLabel}>{metric.label}</p>
                <p className={styles.metricValue}>
                  {isVisible ? (
                    <AnimatedCounter
                      target={metric.value}
                      suffix={metric.suffix}
                      decimals={metric.suffix === 'ms' ? 0 : 1}
                    />
                  ) : (
                    `0${metric.suffix}`
                  )}
                </p>
                <p className={styles.metricDescription}>{metric.description}</p>
              </Card>
            </SectionReveal>
          ))}
        </div>

        <SectionReveal delay={0.4}>
          <div className={styles.miniStats}>
            <div className={styles.miniStat}>
              <span className={styles.miniValue}>4</span>
              <span className={styles.miniLabel}>Document Categories</span>
            </div>
            <div className={styles.miniDivider} aria-hidden="true" />
            <div className={styles.miniStat}>
              <span className={styles.miniValue}>400</span>
              <span className={styles.miniLabel}>Training Samples</span>
            </div>
            <div className={styles.miniDivider} aria-hidden="true" />
            <div className={styles.miniStat}>
              <span className={styles.miniValue}>533</span>
              <span className={styles.miniLabel}>Hybrid Features</span>
            </div>
            <div className={styles.miniDivider} aria-hidden="true" />
            <div className={styles.miniStat}>
              <span className={styles.miniValue}>GridSearchCV</span>
              <span className={styles.miniLabel}>Hyperparameter Tuning</span>
            </div>
          </div>
        </SectionReveal>
      </Con