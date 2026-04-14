import styles from './Scene3D.module.css';

export function Scene3D() {
  return (
    <div className={styles.visual}>
      <div className={styles.mockup} aria-hidden="true">
        <span className={styles.signalHalo} />
        <span className={styles.signalHaloSecondary} />

        <div className={styles.chrome}>
          <div className={styles.chromeDots}>
            <span className={styles.dot} />
            <span className={styles.dot} />
            <span className={styles.dot} />
          </div>
          <span className={styles.chromeLabel}>Invoice Extraction</span>
        </div>

        <div className={styles.body}>
          <div className={styles.previewPane}>
            <div className={styles.previewHeader}>
              <span className={styles.previewBadge}>Source PDF</span>
              <span className={styles.previewMeta}>1 page</span>
            </div>

            <div className={styles.previewPaper}>
              <span className={styles.scanLine} />
              <span className={styles.scanGlow} />

              <div className={styles.paperTopRow}>
                <span className={styles.paperMark} />
                <span className={styles.paperLineShort} />
              </div>
              <div className={styles.paperLineLong} />
              <div className={styles.paperLineMid} />
              <div className={styles.paperLineShort} />
              <div className={styles.paperHighlight} />
              <div className={styles.paperLineLong} />
              <div className={styles.paperLineMid} />
            </div>
          </div>

          <div className={styles.resultPane}>
            <div className={styles.resultHeader}>
              <span className={styles.resultBadge}>Invoice</span>
              <div className={styles.confidenceCluster}>
                <span className={styles.liveSignal}>
                  <span className={styles.liveDot} />
                  Live
                </span>
                <span className={styles.confidence}>94.3%</span>
              </div>
            </div>

            <div className={styles.statusRail}>
              <span className={styles.statusRailLabel}>Extraction in sync</span>
              <span className={styles.statusRailTrack}>
                <span className={styles.statusRailFill} />
              </span>
            </div>

            <div className={styles.fieldGrid}>
              <div className={styles.fieldCard}>
                <span className={styles.fieldLabel}>Invoice Number</span>
                <span className={styles.fieldValue}>INV-2025-00847</span>
              </div>
              <div className={`${styles.fieldCard} ${styles.fieldCardPulse}`}>
                <span className={styles.fieldLabel}>Due Date</span>
                <span className={styles.fieldValue}>2025-02-14</span>
              </div>
            </div>

            <div className={styles.amountCard}>
              <span className={styles.amountLabel}>Total Amount</span>
              <span className={styles.amountValue}>EUR 12,480.00</span>
            </div>

            <div className={styles.summary}>
              <span className={styles.summaryTitle}>Validated extraction</span>
              <span className={styles.summaryText}>
                Structured invoice fields are ready for downstream analysis.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
