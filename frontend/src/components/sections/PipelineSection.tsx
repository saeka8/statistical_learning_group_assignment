import { motion } from 'motion/react';
import { useState } from 'react';
import { pipelineSteps } from '../../data/sampleData';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { SectionReveal } from '../common/SectionReveal';
import { Container } from '../layout/Container';
import styles from './PipelineSection.module.css';

export function PipelineSection() {
  const reducedMotion = usePrefersReducedMotion();
  const summaryPills = ['5 stages', '6 classes', 'Invoice extraction on demand'];
  const [visibleSteps, setVisibleSteps] = useState<Record<string, boolean>>({});

  return (
    <section
      id="pipeline"
      className={`section-padding ${styles.section}`}
      aria-labelledby="pipeline-title"
    >
      <Container>
        <SectionReveal>
          <div className={styles.header}>
            <Badge label="Method" variant="accent" size="md" />
            <h2 id="pipeline-title" className={styles.title}>
              Classical pipeline
            </h2>
            <p className={styles.subtitle}>
              Five deliberate steps take each page from raw input to validated invoice fields.
            </p>
          </div>
        </SectionReveal>

        <SectionReveal delay={0.14}>
          <div className={styles.pipelineShell}>
            <div className={styles.pipelineSummary}>
              <span className={styles.pipelineEyebrow}>Process view</span>
              <h3 className={styles.pipelineLeadTitle}>One document, one deliberate handoff.</h3>
              <p className={styles.pipelineLeadText}>
                Each stage adds structure, confidence, and validation so the model feels legible
                from ingestion to invoice fields.
              </p>

              <div className={styles.pipelineSummaryStats}>
                {summaryPills.map((item) => (
                  <span key={item} className={styles.summaryPill}>
                    {item}
                  </span>
                ))}
              </div>

              <Card variant="glass" padding="md" className={styles.disclaimerCard}>
                <p className={styles.disclaimerText}>
                  Traditional ML only: OCR, handcrafted features, ensemble classification, and
                  regex-assisted entity extraction. No generative models are used in the workflow.
                </p>
              </Card>
            </div>

            <div className={styles.pipelineTrack}>
              {pipelineSteps.map((step, i) => (
                <motion.div
                  key={step.id}
                  data-pipeline-step={step.id}
                  data-in-view={visibleSteps[step.id] ? 'true' : 'false'}
                  className={`${styles.stepWrapper} ${i % 2 === 0 ? styles.stepLeft : styles.stepRight}`}
                  initial={reducedMotion ? undefined : { opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: false, margin: '-40px' }}
                  onViewportEnter={() =>
                    setVisibleSteps((current) => ({ ...current, [step.id]: true }))
                  }
                  onViewportLeave={() =>
                    setVisibleSteps((current) => ({ ...current, [step.id]: false }))
                  }
                  transition={{
                    duration: 0.6,
                    delay: reducedMotion ? 0 : i * 0.12,
                    ease: [0.16, 1, 0.3, 1],
                  }}
                >
                  <div className={styles.stepGhost} aria-hidden="true" />

                  <div className={styles.stepMarker} aria-hidden="true">
                    <span>{String(i + 1).padStart(2, '0')}</span>
                  </div>

                  <div className={styles.stepPanel}>
                    <Card variant="elevated" padding="lg" hoverable className={styles.stepCard}>
                      <div className={styles.stepMeta}>
                        <span className={styles.stepState}>{step.status}</span>
                        <div className={styles.stepIcon}>{step.icon}</div>
                      </div>
                      <h3 className={styles.stepTitle}>{step.title}</h3>
                      <p className={styles.stepDescription}>{step.description}</p>
                      <div className={styles.techniques}>
                        {step.techniques.slice(0, 3).map((tech) => (
                          <span key={tech} className={styles.techChip}>
                            {tech}
                          </span>
                        ))}
                      </div>
                    </Card>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </SectionReveal>
      </Container>
    </section>
  );
}
