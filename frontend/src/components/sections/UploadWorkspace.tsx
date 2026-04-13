import { useCallback, useRef, useState, type ChangeEvent, type DragEvent } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { sampleDocuments } from '../../data/sampleData';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import type { AnalysisPhase, UploadedDocument } from '../../types';
import { formatFileSize } from '../../utils/helpers';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { SectionReveal } from '../common/SectionReveal';
import { StatusIndicator } from '../common/StatusIndicator';
import { Container } from '../layout/Container';
import styles from './UploadWorkspace.module.css';

interface UploadWorkspaceProps {
  documents: UploadedDocument[];
  phase: AnalysisPhase;
  activeDocumentId: string | null;
  onAddFiles: (files: FileList | File[]) => void;
  onRemoveDocument: (id: string) => void;
  onLoadSample: (sampleId: string) => void;
  onAnalyze: () => void;
  onReset: () => void;
  onSetActive: (id: string) => void;
}

const sampleGlyphs = {
  invoice: 'INV',
  contract: 'CTR',
  technical_report: 'RPT',
  email: 'EML',
} as const;

export function UploadWorkspace({
  documents,
  phase,
  activeDocumentId,
  onAddFiles,
  onRemoveDocument,
  onLoadSample,
  onAnalyze,
  onReset,
  onSetActive,
}: UploadWorkspaceProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const reducedMotion = usePrefersReducedMotion();
  const dragCounter = useRef(0);

  const handleDragEnter = useCallback((e: DragEvent) => {
    e.preventDefault();
    dragCounter.current += 1;
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    dragCounter.current -= 1;
    if (dragCounter.current === 0) setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      dragCounter.current = 0;
      if (e.dataTransfer.files.length > 0) {
        onAddFiles(e.dataTransfer.files);
      }
    },
    [onAddFiles]
  );

  const handleFileChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        onAddFiles(e.target.files);
      }
    },
    [onAddFiles]
  );

  const isProcessing = [
    'uploading',
    'preprocessing',
    'extracting_features',
    'classifying',
    'extracting_invoice',
  ].includes(phase);

  return (
    <section id="workspace" className="section-padding" aria-labelledby="workspace-title">
      <Container>
        <SectionReveal>
          <div className={styles.header}>
            <Badge label="Analysis Workspace" variant="accent" size="md" />
            <h2 id="workspace-title" className={styles.title}>
              Stage a live document analysis
            </h2>
            <p className={styles.subtitle}>
              Load a real file or a curated sample, then let the model classify the document and
              surface invoice entities in a single calm workspace built for presentation.
            </p>
          </div>
        </SectionReveal>

        <SectionReveal delay={0.15}>
          <div className={styles.workspaceGrid}>
            <div className={styles.uploadCol}>
              <Card variant="glass" padding="lg">
                <div
                  className={`${styles.dropzone} ${isDragging ? styles.dropzoneActive : ''}`}
                  onDragEnter={handleDragEnter}
                  onDragLeave={handleDragLeave}
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                  role="button"
                  tabIndex={0}
                  aria-label="Upload documents by drag and drop or click to browse"
                  onClick={() => fileInputRef.current?.click()}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      fileInputRef.current?.click();
                    }
                  }}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="sr-only"
                    accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
                    multiple
                    onChange={handleFileChange}
                    aria-hidden="true"
                    tabIndex={-1}
                  />

                  <div className={styles.dropzoneIcon} aria-hidden="true">
                    <svg width="52" height="52" viewBox="0 0 52 52" fill="none">
                      <rect
                        x="5"
                        y="9"
                        width="42"
                        height="34"
                        rx="8"
                        fill="rgba(22, 147, 198, 0.08)"
                        stroke="var(--color-accent-indigo)"
                        strokeWidth="1.5"
                      />
                      <circle
                        cx="26"
                        cy="26"
                        r="10"
                        stroke="var(--color-accent-amber)"
                        strokeWidth="1.5"
                      />
                      <path
                        d="M26 20v12M20 26h12"
                        stroke="var(--color-accent-indigo)"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                      />
                    </svg>
                  </div>

                  <p className={styles.dropzoneTitle}>
                    {isDragging ? 'Release to stage the document' : 'Drag in a document'}
                  </p>
                  <p className={styles.dropzoneHint}>PDF, PNG, JPG, TIFF - or click to browse</p>
                </div>

                <div className={styles.samples}>
                  <p className={styles.samplesLabel}>Or load a curated sample set:</p>
                  <div className={styles.sampleButtons}>
                    {sampleDocuments.map((sample) => (
                      <button
                        key={sample.id}
                        className={styles.sampleBtn}
                        onClick={() => onLoadSample(sample.id)}
                        disabled={isProcessing}
                      >
                        <span className={styles.sampleIcon}>{sampleGlyphs[sample.category]}</span>
                        <span className={styles.sampleName}>{sample.name}</span>
                        <span className={styles.sampleSize}>{formatFileSize(sample.size)}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </Card>
            </div>

            <div className={styles.fileCol}>
              <Card variant="default" padding="lg">
                <div className={styles.fileHeader}>
                  <h3 className={styles.fileTitle}>Document Queue</h3>
                  {documents.length > 0 && (
                    <Badge
                      label={`${documents.length} file${documents.length > 1 ? 's' : ''}`}
                      variant="info"
                    />
                  )}
                </div>

                {documents.length === 0 ? (
                  <div className={styles.emptyState}>
                    <p className={styles.emptyText}>No documents staged yet.</p>
                    <p className={styles.emptyHint}>Upload a file or load a sample to get started.</p>
                  </div>
                ) : (
                  <ul className={styles.fileList} role="list">
                    <AnimatePresence mode="popLayout">
                      {documents.map((doc) => (
                        <motion.li
                          key={doc.id}
                          layout={!reducedMotion}
                          initial={reducedMotion ? undefined : { opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={reducedMotion ? undefined : { opacity: 0, x: -20 }}
                          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                          className={`${styles.fileItem} ${activeDocumentId === doc.id ? styles.fileItemActive : ''}`}
                          onClick={() => onSetActive(doc.id)}
                          role="button"
                          tabIndex={0}
                          aria-selected={activeDocumentId === doc.id}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              onSetActive(doc.id);
                            }
                          }}
                        >
                          <div className={styles.fileInfo}>
                            <span className={styles.fileName}>{doc.name}</span>
                            <span className={styles.fileMeta}>{formatFileSize(doc.size)}</span>
                          </div>
                          <div className={styles.fileActions}>
                            <StatusIndicator status={doc.status} />
                            <button
                              className={styles.removeBtn}
                              onClick={(e) => {
                                e.stopPropagation();
                                onRemoveDocument(doc.id);
                              }}
                              aria-label={`Remove ${doc.name}`}
                              disabled={isProcessing}
                            >
                              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                                <path
                                  d="M2 2l8 8M10 2L2 10"
                                  stroke="currentColor"
                                  strokeWidth="1.5"
                                  strokeLinecap="round"
                                />
                              </svg>
                            </button>
                          </div>
                          {(doc.status === 'uploading' || doc.status === 'processing') && (
                            <div className={styles.progressTrack}>
                              <div className={styles.progressFill} style={{ width: `${doc.progress}%` }} />
                            </div>
                          )}
                        </motion.li>
                      ))}
                    </AnimatePresence>
                  </ul>
                )}

                <div className={styles.controlBar}>
                  <Button
                    variant="primary"
                    size="md"
                    onClick={onAnalyze}
                    disabled={documents.length === 0 || isProcessing}
                    loading={isProcessing}
                    icon={
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <path
                          d="M8 1v6l4-2"
                          stroke="currentColor"
                          strokeWidth="1.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                        <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.5" />
                      </svg>
                    }
                  >
                    {isProcessing ? 'Analyzing...' : 'Analyze All'}
                  </Button>
                  {documents.length > 0 && (
                    <Button variant="ghost" size="md" onClick={onReset} disabled={isProcessing}>
                      Clear All
                    </Button>
                  )}
                </div>

                {isProcessing && (
                  <div className={styles.phaseIndicator}>
                    <div className={styles.phaseBar}>
                      <div
                        className={styles.phaseFill}
                        style={{
                          width:
                            phase === 'uploading'
                              ? '20%'
                              : phase === 'preprocessing'
                                ? '40%'
                                : phase === 'extracting_features'
                                  ? '60%'
                                  : phase === 'classifying'
                                    ? '80%'
                                    : phase === 'extracting_invoice'
                                      ? '90%'
                                      : '100%',
                        }}
                      />
                    </div>
                    <span className={styles.phaseLabel}>
                      {phase === 'uploading' && 'Uploading documents...'}
                      {phase === 'preprocessing' && 'Preprocessing and OCR...'}
                      {phase === 'extracting_features' && 'Extracting features (TF-IDF, layout)...'}
                      {phase === 'classifying' && 'Running ensemble classifier...'}
                      {phase === 'extracting_invoice' && 'Extracting invoice fields (NER, regex)...'}
                    </span>
                  </div>
                )}
              </Card>
            </div>
          </div>
        </SectionReveal>
      </Container>
    </section>
  );
}
