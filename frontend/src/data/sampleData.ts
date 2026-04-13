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
  { category: 'contract', label: 'Contract', confidence: 0, icon: 'CTR' },
  { category: 'technical_report', label: 'Technical Report', confidence: 0, icon: 'RPT' },
  { category: 'email', label: 'Email', confidence: 0, icon: 'EML' },
  { category: 'receipt', label: 'Receipt', confidence: 0, icon: 'RCT' },
  { category: 'letter', label: 'Letter', confidence: 0, icon: 'LTR' },
];

export const sampleInvoiceClassification: ClassificationResult = {
  predictedCategory: 'invoice',
  predictedLabel: 'Invoice',
  scores: [
    { category: 'invoice', label: 'Invoice', confidence: 0.943, icon: 'INV' },
    { category: 'receipt', label: 'Receipt', confidence: 0.031, icon: 'RCT' },
    { category: 'contract', label: 'Contract', confidence: 0.012, icon: 'CTR' },
    { category: 'letter', label: 'Letter', confidence: 0.008, icon: 'LTR' },
    { category: 'technical_report', label: 'Technical Report', confidence: 0.004, icon: 'RPT' },
    { category: 'email', label: 'Email', confidence: 0.002, icon: 'EML' },
  ],
  processingTimeMs: 342,
};

export const sampleContractClassification: ClassificationResult = {
  predictedCategory: 'contract',
  predictedLabel: 'Contract',
  scores: [
    { category: 'contract', label: 'Contract', confidence: 0.891, icon: 'CTR' },
    { category: 'letter', label: 'Letter', confidence: 0.054, icon: 'LTR' },
    { category: 'invoice', label: 'Invoice', confidence: 0.028, icon: 'INV' },
    { category: 'technical_report', label: 'Technical Report', confidence: 0.015, icon: 'RPT' },
    { category: 'email', label: 'Email', confidence: 0.008, icon: 'EML' },
    { category: 'receipt', label: 'Receipt', confidence: 0.004, icon: 'RCT' },
  ],
  processingTimeMs: 287,
};

export const sampleReportClassification: ClassificationResult = {
  predictedCategory: 'technical_report',
  predictedLabel: 'Technical Report',
  scores: [
    { category: 'technical_report', label: 'Technical Report', confidence: 0.917, icon: 'RPT' },
    { category: 'email', label: 'Email', confidence: 0.038, icon: 'EML' },
    { category: 'letter', label: 'Letter', confidence: 0.022, icon: 'LTR' },
    { category: 'contract', label: 'Contract', confidence: 0.013, icon: 'CTR' },
    { category: 'invoice', label: 'Invoice', confidence: 0.006, icon: 'INV' },
    { category: 'receipt', label: 'Receipt', confidence: 0.004, icon: 'RCT' },
  ],
  processingTimeMs: 305,
};

export const sampleEmailClassification: ClassificationResult = {
  predictedCategory: 'email',
  predictedLabel: 'Email',
  scores: [
    { category: 'email', label: 'Email', confidence: 0.872, icon: 'EML' },
    { category: 'letter', label: 'Letter', confidence: 0.071, icon: 'LTR' },
    { category: 'contract', label: 'Contract', confidence: 0.029, icon: 'CTR' },
    { category: 'technical_report', label: 'Technical Report', confidence: 0.016, icon: 'RPT' },
    { category: 'invoice', label: 'Invoice', confidence: 0.008, icon: 'INV' },
    { category: 'receipt', label: 'Receipt', confidence: 0.004, icon: 'RCT' },
  ],
  processingTimeMs: 251,
};

export const sampleInvoiceExtraction: InvoiceExtractionResult = {
  invoiceNumber: {
    key: 'invoiceNumber',
    label: 'Invoice Number',
    value: 'INV-2025-00847',
    confidence: 0.98,
  },
  invoiceDate: {
    key: 'invoiceDate',
    label: 'Invoice Date',
    value: '2025-01-15',
    confidence: 0.96,
  },
  dueDate: {
    key: 'dueDate',
    label: 'Due Date',
    value: '2025-02-14',
    confidence: 0.93,
  },
  issuerName: {
    key: 'issuerName',
    label: 'Issuer Name',
    value: 'Nexus Technology Solutions Ltd.',
    confidence: 0.97,
  },
  recipientName: {
    key: 'recipientName',
    label: 'Recipient Name',
    value: 'Arcadia Digital Ventures GmbH',
    confidence: 0.95,
  },
  totalAmount: {
    key: 'totalAmount',
    label: 'Total Amount',
    value: 'EUR 12,480.00',
    confidence: 0.99,
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
    techniques: ['TF-IDF vectors', 'N-gram features', 'Layout heuristics', 'Structural patterns'],
    icon: 'FX',
    status: 'complete',
  },
  {
    id: 'classification',
    title: 'Document Classification',
    description: 'An ensemble of classical models selects one document class from the known set.',
    techniques: ['SVM classifier', 'Random Forest', 'Logistic Regression', 'Ensemble voting'],
    icon: 'CLS',
    status: 'complete',
  },
  {
    id: 'extraction',
    title: 'Invoice Field Extraction',
    description: 'Invoices trigger structured extraction and validation of high-value business fields.',
    techniques: ['Regex patterns', 'Named Entity Recognition', 'Spatial analysis', 'Field validation'],
    icon: 'NER',
    status: 'complete',
  },
];

export const sampleMetrics: MetricCard[] = [
  {
    label: 'Classification Accuracy',
    value: 94.7,
    suffix: '%',
    description: 'Weighted average across all 6 document categories on the held-out test set.',
    color: 'var(--color-accent-indigo)',
  },
  {
    label: 'Macro F1-Score',
    value: 92.3,
    suffix: '%',
    description: 'Harmonic mean of precision and recall, macro-averaged over all classes.',
    color: 'var(--color-accent-blue)',
  },
  {
    label: 'Invoice Extraction Completeness',
    value: 96.1,
    suffix: '%',
    description: 'Percentage of invoice fields correctly identified and extracted from test invoices.',
    color: 'var(--color-accent-emerald)',
  },
  {
    label: 'Avg. Processing Time',
    value: 310,
    suffix: 'ms',
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
    confidence: 0.943,
    extraction: sampleInvoiceExtraction,
  },
  {
    id: 'cs2',
    documentName: 'nda_agreement_v3.pdf',
    documentType: 'PDF - Digital Contract',
    previewPlaceholder: 'CONTRACT',
    classifiedAs: 'contract',
    classifiedLabel: 'Contract',
    confidence: 0.891,
  },
  {
    id: 'cs3',
    documentName: 'q4_analysis_report.pdf',
    documentType: 'PDF - Technical Report',
    previewPlaceholder: 'REPORT',
    classifiedAs: 'technical_report',
    classifiedLabel: 'Technical Report',
    confidence: 0.917,
  },
];

export interface SampleDocument {
  id: string;
  name: string;
  type: string;
  size: number;
  category: 'invoice' | 'contract' | 'technical_report' | 'email';
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
    id: 'sample_contract',
    name: 'nda_agreement_v3.pdf',
    type: 'application/pdf',
    size: 512340,
    category: 'contract',
    classification: sampleContractClassification,
  },
  {
    id: 'sample_report',
    name: 'q4_performance_analysis.pdf',
    type: 'application/pdf',
    size: 1048576,
    category: 'technical_report',
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
