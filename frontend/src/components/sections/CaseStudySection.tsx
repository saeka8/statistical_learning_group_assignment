import { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { caseStudies } from '../../data/sampleData';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import type { CaseStudy } from '../../types';
import { formatConfidence, getCategoryColor } from '../../utils/helpers';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { ConfidenceBar } from '../common/ConfidenceBar';
import { SectionReveal } from '../common/SectionReveal';
import { Container } from '../layout/Container';
import styles from './CaseStudySection.module.css';

function CaseStudyCard({
  study,
  isActive,
  onClick,
}: {
  study: CaseStudy;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <Card
      variant={isActive ? 'accent' : 'elevated'}
      padding="none"
      hoverable
      className={`${styles.caseCard} ${isActive ? styles.caseCardActive : ''}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-pressed={isActive}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
    >
      <div className={styles.preview} style={{ borderColor: getCategoryColor(study.classifiedAs) }}>
        <div className={styles.previewContent}>
          <div className={styles.previewLines} aria-hidden="true">
            <div className={styles.previewLine} style={{ width: '60%' }} />
            <div className={styles.previewLine} style={{ width: '80%' }} />
            <div className={styles.previewLine} style={{ width: '45%' }} />
            <div className={styles.previewLine} style={{ width: '70%' }} />
            <div className={styles.previewLine} style={{ width: '55%' }} />
          </div>
          <span className={styles.previewLabel}>{study.previewPlaceholder}</span>
        </div>
      </div>

      <div className={styles.caseBody}>
        <p className={styles.caseName}>{study.documentName}</p>
        <p className={styles.caseType}>{study.documentType}</p>

        <div className={styles.caseResult}>
          <Badge
            label={study.classifiedLabel}
            variant={study.classifiedAs === 'invoice' ? 'accent' : 'default'}
            size="md"
          />
          <span className={styles.caseConfidence}>{formatConfidence(study.confidence)}</span>
        </div>
      </div>
    </Card>
  );
}

export function CaseStudySection() {
  const [activeStudy, setActiveStudy] = useState<CaseStudy>(caseStudies[0]);
  const reducedMotion = usePrefersReducedMotion();

  return (
    <section id="cases" className={`section-padding ${styles.section}`} aria-labelledby="cases-title">
      <Container>
        <SectionReveal>
          <div className={styles.header}>
            <Badge label="Case Studies" variant="accent" size="md" />
            <h2 id="cases-title" className={styles.title}>
              Real Document Examples
            </h2>
            <p className={styles.subtitle}>
              See the full pipeline in action — from raw document to classified category and
              extracted invoice fields.
            </p>
          </div>
        </SectionReveal>

        <div className={styles.caseGrid}>
          <div className={styles.selector}>
            {caseStudies.map((study, i) => (
              <SectionReveal key={study.id} delay={i * 0.1}>
                <CaseStudyCard
                  study={study}
                  isActive={activeStudy.id === study.id}
                  onClick={() => setActiveStudy(study)}
                />
              </SectionReveal>
            ))}
          </div>

          <div className={styles.detail}>
            <AnimatePresence mode="wait">
              <motion.div
                key={activeStudy.id}
                initial={reducedMotion ? undefined : { opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={reducedMotion ? undefined : { opacity: 0, x: -20 }}
                transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              >
                <Card variant="elevated" padding="lg">
                  <div className={styles.detailHeader}>
                    <h3 className={styles.detailTitle}>{activeStudy.documentName}</h3>
                    <Badge label={activeStudy.classifiedLabel} variant="accent" size="md" />
                  </div>

                  <div className={styles.detailMeta}>
                    <span>{activeStudy.documentType}</span>
                    <span>•</span>
                    <span>Confidence: {formatConfidence(activeStudy.confidence)}</span>
                  </div>

                  <div className={styles.detailBar}>
                    <ConfidenceBar
                      value={activeStudy.confidence}
                      label="Classification Confidence"
                      color={getCategoryColor(activeStudy.classifiedAs)}
                      size="lg"
                    />
                  </div>

                  {activeStudy.extraction && (
                    <div className={styles.detailExtraction}>
                      <h4 className={styles.extractionTitle}>Extracted Invoice Fields</h4>
                      <div className={styles.extractionGrid}>
                        {Object.values(activeStudy.extraction).map((field) => {
                          if (!field || typeof field !== 'object' || !('key' in field)) return null;
                          return (
                            <div key={field.key} className={styles.extractionField}>
                              <span className={styles.extractionLabel}>{field.label}</span>
                              <span className={styles.extractionValue}>{field.value}</span>
                              <ConfidenceBar
                                value={field.confidence}
                                size="sm"
                                color="var(--color-accent-emerald)"
                              />
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {!activeStudy.extraction && (
                    <div className={styles.noExtraction}>
                      <p>
                        This document was classified as <strong>{activeStudy.classifiedLabel}</strong>,
                        so invoice field extraction was not performed. Extraction is triggered only
                        when a document is classified as an Invoice.
                      </p>
                    </div>
                  )}
                </Card>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </Container>
    </section>
  );
}
