import { AnimatePresence, motion } from 'motion/react';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import type { ClassificationResult } from '../../types';
import { formatConfidence, getCategoryBg, getCategoryColor } from '../../utils/helpers';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { ConfidenceBar } from '../common/ConfidenceBar';
import { SectionReveal } from '../common/SectionReveal';
import { Container } from '../layout/Container';
import styles from './ClassificationResults.module.css';

interface ClassificationResultsProps {
  result: ClassificationResult | null;
  isVisible: boolean;
}

export function ClassificationResults({ result, isVisible }: ClassificationResultsProps) {
  const reducedMotion = usePrefersReducedMotion();

  if (!isVisible || !result) return null;

  return (
    <section className="section-padding" aria-labelledby="classification-title">
      <Container>
        <SectionReveal>
          <div className={styles.header}>
            <Badge label="Classification Result" variant="accent" size="md" />
            <h2 id="classification-title" className={styles.title}>
              The model&apos;s final decision
            </h2>
            <p className={styles.subtitle}>
              A primary class is selected, then compared against the closest alternatives so the
              decision reads clearly during a live demo.
            </p>
          </div>
        </SectionReveal>

        <AnimatePresence mode="wait">
          <motion.div
            key={result.predictedCategory}
            initial={reducedMotion ? undefined : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reducedMotion ? undefined : { opacity: 0, y: -10 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className={styles.predictedWrapper}>
              <Card variant="accent" padding="lg" className={styles.predictedCard}>
                <div className={styles.predictedInner}>
                  <div className={styles.predictedLeft}>
                    <span className={styles.predictedIcon}>
                      {result.scores.find((s) => s.category === result.predictedCategory)?.icon}
                    </span>
                    <div>
                      <p className={styles.predictedLabel}>Model decision</p>
                      <h3 className={styles.predictedCategory}>{result.predictedLabel}</h3>
                    </div>
                  </div>
                  <div className={styles.predictedRight}>
                    <span className={styles.confidenceValue}>
                      {formatConfidence(result.scores[0].confidence)}
                    </span>
                    <span className={styles.confidenceLabel}>top confidence</span>
                    <span className={styles.timeLabel}>latency {result.processingTimeMs}ms</span>
                  </div>
                </div>
              </Card>
            </div>

            <div className={styles.scoresGrid}>
              {result.scores.map((score, i) => {
                const isPredicted = score.category === result.predictedCategory;
                return (
                  <motion.div
                    key={score.category}
                    initial={reducedMotion ? undefined : { opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: reducedMotion ? 0 : i * 0.08 }}
                  >
                    <Card
                      variant={isPredicted ? 'accent' : 'default'}
                      padding="md"
                      hoverable
                      className={styles.scoreCard}
                    >
                      <div className={styles.scoreHeader}>
                        <span className={styles.scoreIcon}>{score.icon}</span>
                        <span className={styles.scoreName}>{score.label}</span>
                        {isPredicted && <Badge label="Predicted" variant="accent" />}
                      </div>
                      <ConfidenceBar
                        value={score.confidence}
                        color={
                          isPredicted
                            ? getCategoryColor(score.category)
                            : 'var(--color-bg-tertiary)'
                        }
                        size="md"
                        highlighted={isPredicted}
                      />
                      <p
                        className={styles.scoreValue}
                        style={{
                          color: isPredicted
                            ? getCategoryColor(score.category)
                            : 'var(--color-text-tertiary)',
                          background: isPredicted ? getCategoryBg(score.category) : 'transparent',
                        }}
                      >
                        {formatConfidence(score.confidence)}
                      </p>
                    </Card>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        </AnimatePresence>
      </Container>
    </section>
  );
}
