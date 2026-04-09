import { motion } from 'motion/react';
import { pipelineSteps } from '../../data/sampleData';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { SectionReveal } from '../common/SectionReveal';
import { Container } from '../layout/Container';
import styles from './PipelineSection.module.css';

export function PipelineSection() {
  const reducedMotion = usePrefersReducedMotion();

  return (
    <section
      id="pipeline"
      className={`section-padding ${styles.section}`}
      aria-labelledby="pipeline-title"
    >
      <Container>
        <SectionReveal>
          <div className={styles.header}>
            <Badge label="Methodology" variant="accent" size="md" />
            <h2 id="pipeline-title" className={styles.title}>
              How the system reads a page
            </h2>
            <p className={styles.subtitle}>
              This interface tells a clear story: each document moves through a classical pipeline,
              from raw input to verified extraction, with no generative models hidden behind the
              scenes.
            </p>
          </div>
        </SectionReveal>

        <div className={styles.pipeline}>
          {pipelineSteps.map((step, i) => (
            <motion.div
              key={step.id}
              className={styles.stepWrapper}
              initial={reducedMotion ? undefined : { opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{
                duration: 0.6,
                delay: reducedMotion ? 0 : i * 0.12,
                ease: [0.16, 1, 0.3, 1],
              }}
            >
              <Card variant="elevated" padding="lg" hoverable className={styles.stepCard}>
                <div className={styles.stepMeta}>
                  <div className={styles.stepNumber} aria-hidden="true">
                    <span>{String(i + 1).padStart(2, '0')}</span>
                  </div>
                  <span className={styles.stepState}>{step.status}</span>
                </div>
                <div className={styles.stepIcon}>{step.icon}</div>
                <h3 className={styles.stepTitle}>{step.title}</h3>
                <p className={styles.stepDescription}>{step.description}</p>
                <div className={styles.techniques}>
                  {step.techniques.map((tech) => (
                    <span key={tech} className={styles.techChip}>
                      {tech}
                    </span>
                  ))}
                </div>
              </Card>
            </motion.div>
          ))}
        </div>

        <SectionReveal delay={0.3}>
          <div className={styles.disclaimer}>
            <Card variant="glass" padding="md">
              <p className={styles.disclaimerText}>
                <strong>Important:</strong> this project exclusively uses traditional statistical
                learning and machine learning methods such as SVM, Random Forest, TF-IDF, OCR, and
                regex-based NER. No generative AI, LLMs, or transformer-based generation models are
                used in the classification or extraction pipeline.
              </p>
            </Card>
          </div>
        </SectionReveal>
      </Container>
    </section>
  );
}
