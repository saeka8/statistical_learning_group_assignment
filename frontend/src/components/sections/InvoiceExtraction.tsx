import { motion } from 'motion/react';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';
import type { ExtractedField, InvoiceExtractionResult } from '../../types';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { ConfidenceBar } from '../common/ConfidenceBar';
import { SectionReveal } from '../common/SectionReveal';
import { Container } from '../layout/Container';
import styles from './InvoiceExtraction.module.css';

interface InvoiceExtractionProps {
  activeDocumentName: string;
  result: InvoiceExtractionResult | null;
  isVisible: boolean;
}

function FieldCard({ field, index }: { field: ExtractedField; index: number }) {
  const reducedMotion = usePrefersReducedMotion();

  const getConfidenceVariant = (confidence: number) => {
    if (confidence >= 0.95) return 'success';
    if (confidence >= 0.85) return 'info';
    if (confidence >= 0.7) return 'warning';
    return 'error';
  };

  return (
    <motion.div
      className={field.key === 'totalAmount' ? styles.featuredField : ''}
      initial={reducedMotion ? undefined : { opacity: 0, y: 15, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        duration: 0.5,
        delay: reducedMotion ? 0 : index * 0.1,
        ease: [0.16, 1, 0.3, 1],
      }}
    >
      <Card
        variant="default"
        padding="md"
        hoverable
        className={`${styles.fieldCard} ${field.key === 'totalAmount' ? styles.fieldCardEmphasis : ''}`}
      >
        <div className={styles.fieldHeader}>
          <span className={styles.fieldLabel}>{field.label}</span>
          <Badge
            label={`${(field.confidence * 100).toFixed(0)}%`}
            variant={getConfidenceVariant(field.confidence)}
            size="sm"
          />
        </div>
        <p className={styles.fieldValue}>{field.value}</p>
        <ConfidenceBar
          value={field.confidence}
          size="sm"
          color={
            field.confidence >= 0.95
              ? 'var(--color-accent-emerald)'
              : field.confidence >= 0.85
                ? 'var(--color-accent-blue)'
                : 'var(--color-accent-amber)'
          }
        />
      </Card>
    </motion.div>
  );
}

export function InvoiceExtraction({
  activeDocumentName,
  result,
  isVisible,
}: InvoiceExtractionProps) {
  if (!isVisible || !result) return null;

  const fields: ExtractedField[] = [
    result.invoiceNumber,
    result.invoiceDate,
    result.dueDate,
    result.issuerName,
    result.recipientName,
    result.totalAmount,
  ];

  return (
    <section className="section-padding" aria-labelledby="extraction-title">
      <Container>
        <SectionReveal>
          <div className={styles.header}>
            <Badge label="Invoice Extraction" variant="success" size="md" dot />
            <h2 id="extraction-title" className={styles.title}>
              Recovered invoice fields
            </h2>
            <p className={styles.subtitle}>
              When the winning class is an invoice, the interface shifts from prediction to the
              fields that matter most.
            </p>
            <div
              className={styles.documentContext}
              role="status"
              aria-live="polite"
              aria-label={`Active document ${activeDocumentName}`}
            >
              <span className={styles.documentContextLabel}>Active document</span>
              <span className={styles.documentContextName}>{activeDocumentName}</span>
            </div>
          </div>
        </SectionReveal>

        <div className={styles.fieldsGrid}>
          {fields.map((field, i) => (
            <FieldCard key={field.key} field={field} index={i} />
          ))}
        </div>

      </Container>
    </section>
  );
}
