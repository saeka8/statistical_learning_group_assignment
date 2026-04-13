import type {
  CaseStudy,
  CategoryScore,
  ClassificationResult,
  InvoiceExtractionResult,
  MetricCard,
  PipelineStep,
} from '../types';

export const allCategories: CategoryScore[] = [
  { category: 'invoice', label: 'Invoice', confidence: 0, icon: 'INV' },
  { category: 'email', label: 'Email', confidence: 0, icon: 'EML' },
  { category: 'resume', label: 'Resume', confidence: 0, icon: 'RES' },
  { category: 'scientific_publication', label: 'Scientific Publication', confidence: 0, icon: 'SCI' },
];

export const sampleInvoiceClassification: ClassificationResult = {
  predictedCategory: 'invoice',
  predictedLabel: 'Invoice',
  scores: [
    { category: 'invoice', label: 'Invoice', confidence: 0.821, icon: 'INV' },
    { category: 'scientific_publication', label: 'Scientific Publication', confidence: 0.112, icon: 'SCI' },
    { category: 'email', label: 'Email', confidence: 0.038, icon: 'EML' },
    { category: 'resume', label: 'Resume', confidence: 0.029, icon: 'RES' },
  ],
  processingTimeMs: 4200,
};

export const sampleResumeClassification: ClassificationResult = {
  predictedCategory: 'resume',
  predictedLabel: 'Resume',
  scores: [
    { category: 'resume', label: 'Resume', confidence: 0.956, icon: 'RES' },
    { category: 'scientific_publication', label: 'Scientific Publication', confidence: 0.023, icon: 'SCI' },
    { category: 'invoice', label: 'Invoice', confidence: 0.012, icon: 'INV' },
    { category: 'email', label: 'Email', confidence: 0.009, icon: 'EML' },
  ],
  processingTimeMs: 3800,
};

export const sampleReportClassification: ClassificationResult = {
  predictedCategory: 'scientific_publication',
  predictedLabel: 'Scientific Publication',
  scores: [
    { category: 'scientific_publication', label: 'Scientific Publication', confidence: 0.710, icon: 'SCI' },
    { category: 'invoice', label: 'Invoice', confidence: 0.175, icon: 'INV' },
    { category: 'resume', label: 'Resume', confidence: 0.068, icon: 'RES' },
    { category: 'email', label: 'Email', confidence: 0.047, icon: 'EML' },
  ],
  processingTimeMs: 5100,
};

export const sampleEmailClassification: ClassificationResult = {
  predictedCategory: 'email',
  predictedLabel: 'Email',
  scores: [
    { category: 'email', label: 'Email', confidence: 0.884, icon: 'EML' },
    { category: 'invoice', label: 'Invoice', confidence: 0.063, icon: 'INV' },
    { category: 'scientific_publication', label: 'Scientific Publication', confidence: 0.028, icon: 'SCI' },
    { category: 'resume', label: 'Resume', confidence: 0.025, icon: 'RES' },
  ],
  processingTimeMs: 3500,
};

export const sampleInvoiceExtraction: InvoiceExtractionResult = {
  invoiceNumber: {
    key: 'invoiceNumber',
    label: 'Invoice Number',
    value: 'INV-2025-00847',
    confidence: 0.85,
  },
  invoiceDate: {
    key: 'invoiceDate',
    label: 'Invoice Date',
    value: '2025-01-15',
    confidence: 0.80,
  },
  dueDate: {
    key: 'dueDate',
    label: 'Due Date',
    value: '2025-02-14',
    confidence: 0.65,
  },
  issuerName: {
    key: 'issuerName',
    label: 'Issuer Name',
    value: 'Nexus Technology Solutions Ltd.',
    confidence: 0.75,
  },
  recipientName: {
    key: 'recipientName',
    label: 'Recipient Name',
    value: 'Arcadia Digital Ventures GmbH',
    confidence: 0.70,
  },
  totalAmount: {
    key: 'totalAmount',
    label: 'Total Amount',
    value: 'EUR 12,480.00',
    confidence: 0.82,
  },
};

export const pipelineSteps: PipelineStep[] = [
  {
    id: 'input',
    title: 'Document Input',
    description: 'PDF or image material is accepted, normalized, and prepared for processing.',
    techniques: ['PDF parsing', 'Image decoding', 'Format normalization'],
    icon: 'IN',
    status: 'complete',
  },
  {
    id: 'preprocessing',
    title: 'Preprocessing',
    description: 'OCR, denoising, layout cleanup, and text normalization create a readable page.',
    techniques: ['Tesseract OCR', 'Binarization', 'Deskewing', 'Text normalization'],
    icon: 'OCR',
    status: 'complete',
  },
  {
    id: 'features',
    title: 'Feature Extraction',
    description: 'The system derives lexical, structural, and visual signals from the document.',
    techniques: ['TF-IDF vectors (500 features)', 'Bigram features', 'HOG descriptors', 'Text density grid', 'Edge & margin features'],
    icon: 'FX',
    status: 'complete',
  },
  {
    id: 'classification',
    title: 'Document Classification',
    description: 'A hybrid NLP + Computer Vision Random Forest model selects one document class.',
    techniques: ['Random Forest (200 trees)', 'Hybrid text + image features (533 total)', 'GridSearchCV tuning'],
    icon: 'CLS',
    status: 'complete',
  },
  {
    id: 'extraction',
    title: 'Invoice Field Extraction',
    description: 'Invoices trigger structured extraction and validation of high-value business fields.',
    techniques: ['Cascading regex patterns', 'Multi-pass search', 'Spatial heuristics', 'Field validation'],
    icon: 'EXT',
    status: 'complete',
  },
];

export const sampleMetrics: MetricCard[] = [
  {
    label: 'Classification Accuracy',
    value: 87.5,
    suffix: '%',
    description: 'Weighted average across all 4 document categories on the held-out test set.',
    color: 'var(--color-accent-indigo)',
  },
  {
    label: 'Macro F1-Score',
    value: 85.2,
    suffix: '%',
    description: 'Harmonic mean of precision and recall, macro-averaged over all classes.',
    color: 'var(--color-accent-blue)',
  },
  {
    label: 'Invoice Extraction Completeness',
    value: 37.0,
    suffix: '%',
    description: 'Percentage of invoice fields correctly extracted from SROIE test invoices.',
    color: 'var(--color-accent-emerald)',
  },
  {
    label: 'Avg. Processing Time',
    value: 4.2,
    suffix: 's',
    description: 'Mean end-to-end latency from document upload to final extraction result.',
    color: 'var(--color-accent-violet)',
  },
];

export const caseStudies: CaseStudy[] = [
  {
    id: 'cs1',
    documentName: 'nexus_invoice_jan2025.pdf',
    documentType: 'PDF - Scanned Invoice',
    previewPlaceholder: 'INVOICE',
    classifiedAs: 'invoice',
    classifiedLabel: 'Invoice',
    confidence: 0.821,
    extraction: sampleInvoiceExtraction,
  },
  {
    id: 'cs2',
    documentName: 'john_doe_resume.png',
    documentType: 'PNG - Scanned Resume',
    previewPlaceholder: 'RESUME',
    classifiedAs: 'resume',
    classifiedLabel: 'Resume',
    confidence: 0.956,
  },
  {
    id: 'cs3',
    documentName: 'neural_networks_survey.pdf',
    documentType: 'PDF - Scientific Publication',
    previewPlaceholder: 'PAPER',
    classifiedAs: 'scientific_publication',
    classifiedLabel: 'Scientific Publication',
    confidence: 0.710,
  },
];

export interface SampleDocument {
  id: string;
  name: string;
  type: string;
  size: number;
  category: 'invoice' | 'email' | 'resume' | 'scientific_publication';
  classification: ClassificationResult;
  extraction?: InvoiceExtractionResult;
}

export const sampleDocuments: SampleDocument[] = [
  {
    id: 'sample_invoice',
    name: 'nexus_invoice_2025.pdf',
    type: 'application/pdf',
    size: 284672,
    category: 'invoice',
    classification: sampleInvoiceClassification,
    extraction: sampleInvoiceExtraction,
  },
  {
    id: 'sample_resume',
    name: 'john_doe_resume.png',
    type: 'image/png',
    size: 172550,
    category: 'resume',
    classification: sampleResumeClassification,
  },
  {
    id: 'sample_report',
    name: 'neural_networks_survey.pdf',
    type: 'application/pdf',
    size: 1048576,
    category: 'scientific_publication',
    classification: sampleReportClassification,
  },
  {
    id: 'sample_email',
    name: 'vendor_correspondence.eml',
    type: 'message/rfc822',
    size: 15820,
    category: 'email',
    classification: sampleEmailClassification,
  },
];
