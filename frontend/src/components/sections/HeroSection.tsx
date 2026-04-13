import { motion } from 'motion/react';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import { Button } from '../common/Button';
import { Scene3D } from '../3d/Scene3D';
import { Container } from '../layout/Container';
import styles from './HeroSection.module.css';

const proofItems = [
  { value: '4', label: 'document classes' },
  { value: '~4 s', label: 'average latency' },
  { value: '87.5%', label: 'classification accuracy' },
];

export function HeroSection() {
  const reducedMotion = usePrefersReducedMotion();

  const animProps = (delay: number) =>
    reducedMotion
      ? {}
      : {
          initial: { opacity: 0, y: 12 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.55, delay, ease: [0.16, 1, 0.3, 1] as const },
        };

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({
      behavior: reducedMotion ? 'auto' : 'smooth',
    });
  };

  return (
    <section className={styles.hero} aria-labelledby="hero-title">
      <div className={styles.bgMesh} aria-hidden="true" />

      <Container size="wide">
        <div className={styles.grid}>
          <div className={styles.content}>
            <motion.div {...animProps(0.05)} className={styles.kickerRow}>
              <span className={styles.eyebrow}>Statistical Learning Project</span>
            </motion.div>

            <motion.div {...animProps(0.12)}>
              <h1 id="hero-title" className={styles.title}>
                Classify documents.
                <br />
                Extract invoice data.
              </h1>
            </motion.div>

            <motion.div {...animProps(0.18)}>
              <p className={styles.subtitle}>
                A cleaner presentation interface for showing how a traditional ML pipeline sorts
                business documents and turns invoices into structured fields.
              </p>
            </motion.div>

            <motion.div {...animProps(0.24)}>
              <div className={styles.actions}>
                <Button size="lg" onClick={() => scrollTo('workspace')}>
                  Open the demo
                </Button>
                <Button variant="outline" size="lg" onClick={() => scrollTo('pipeline')}>
                  View methodology
                </Button>
              </div>
            </motion.div>

            <motion.div {...animProps(0.3)} className={styles.proofStrip}>
              {proofItems.map((item) => (
                <div key={item.label} className={styles.proofCard}>
                  <span className={styles.proofValue}>{item.value}</span>
                  <span className={styles.proofLabel}>{item.label}</span>
                </div>
              ))}
            </motion.div>
          </div>

          <motion.div {...animProps(0.14)} className={styles.visualColumn}>
            <div className={styles.visualFrame} aria-hidden="true">
              <Scene3D />
            </div>
          </motion.div>
        </div>
      </Container>
    </section>
  );
}
