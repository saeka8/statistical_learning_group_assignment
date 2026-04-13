import { Container } from './Container';
import styles from './Footer.module.css';

export function Footer() {
  return (
    <footer className={styles.footer}>
      <Container>
        <div className={styles.inner}>
          <div className={styles.left}>
            <span className={styles.eyebrow}>Academic showcase</span>
            <h3 className={styles.title}>DocLens</h3>
            <p className={styles.description}>
              A cleaner interface for a Statistical Learning and Prediction course project focused
              on document classification and invoice extraction.
            </p>
          </div>

          <div className={styles.right}>
            <div className={styles.meta}>
              <span className={styles.metaLabel}>Course</span>
              <span className={styles.metaValue}>Statistical Learning and Prediction</span>
            </div>
            <div className={styles.meta}>
              <span className={styles.metaLabel}>Methods</span>
              <span className={styles.metaValue}>OCR, TF-IDF, classical ML, regex-assisted NER</span>
            </div>
            <div className={styles.meta}>
              <span className={styles.metaLabel}>Purpose</span>
              <span className={styles.metaValue}>Demo-ready document analysis surface</span>
            </div>
          </div>
        </div>

        <div className={styles.bottom}>
          <p className={styles.copyright}>
            (c) 2026 DocLens. Academic interface built around non-generative methods.
          </p>
        </div>
      </Container>
    </footer>
  );
}
