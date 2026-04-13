import { Container } from './Container';
import styles from './Footer.module.css';

export function Footer() {
  return (
    <footer className={styles.footer}>
      <Container>
        <div className={styles.inner}>
          <div className={styles.left}>
            <h3 className={styles.title}>DocLens</h3>
            <p className={styles.description}>
              Document Classification and Invoice Information Extraction - a group project for the
              Statistical Learning and Prediction course. Built with traditional machine learning,
              NLP, and computer vision methods.
            </p>
          </div>

          <div className={styles.right}>
            <div className={styles.meta}>
              <span className={styles.metaLabel}>Course</span>
              <span className={styles.metaValue}>Statistical Learning and Prediction</span>
            </div>
            <div className={styles.meta}>
              <span className={styles.metaLabel}>Approach</span>
              <span className={styles.metaValue}>Traditional ML / NLP / CV</span>
            </div>
            <div className={styles.meta}>
              <span className={styles.metaLabel}>Focus</span>
              <span className={styles.metaValue}>Classification and invoice extraction</span>
            </div>
          </div>
        </div>

        <div className={styles.bottom}>
          <p className={styles.copyright}>
            (c) 2025 DocLens - Academic project. All analysis uses traditional, non-generative AI.
          </p>
        </div>
      </Container>
    </footer>
  );
}
