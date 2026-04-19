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
    { category: 'invoice', label: 'Invoice', confidence: 0.812, icon: 'INV' },
    { category: 'email', label: 'Email', confidence: 0.094, icon: 'EML' },
    { category: 'scientific_publication', label: 'Scientific Publication', confidence: 0.061, icon: 'SCI' },
    { category: 'resume', label: 'Resume', confidence: 0.033, icon: 'RES' },
  ],
  processingTimeMs: 4200,
};

export const sampleResumeClassification: ClassificationResult = {
  predictedCategory: 'resume',
  predictedLabel: 'Resume',
  scores: [
    { category: 'resume', label: 'Resume', confidence: 0.961, icon: 'RES' },
    { category: 'scientific_publication', label: 'Scientific Publication', confidence: 0.022, icon: 'SCI' },
    { category: 'email', label: 'Email', confidence: 0.012, icon: 'EML' },
    { category: 'invoice', label: 'Invoice', confidence: 0.005, icon: 'INV' },
  ],
  processingTimeMs: 3850,
};

export const sampleScientificClassification: ClassificationResult = {
  predictedCategory: 'scientific_publication',
  predictedLabel: 'Scientific Publication',
  scores: [
    { category: 'scientific_publication', label: 'Scientific Publication', confidence: 0.752, icon: 'SCI' },
    { category: 'resume', label: 'Resume', confidence: 0.131, icon: 'RES' },
    { category: 'email', label: 'Email', confidence: 0.078, icon: 'EML' },
    { category: 'invoice', label: 'Invoice', confidence: 0.039, icon: 'INV' },
  ],
  processingTimeMs: 4380,
};

export const sampleEmailClassification: ClassificationResult = {
  predictedCategory: 'email',
  predictedLabel: 'Email',
  scores: [
    { category: 'email', label: 'Email', confidence: 0.788, icon: 'EML' },
    { category: 'invoice', label: 'Invoice', confidence: 0.118, icon: 'INV' },
    { category: 'scientific_publication', label: 'Scientific Publication', confidence: 0.057, icon: 'SCI' },
    { category: 'resume', label: 'Resume', confidence: 0.037, icon: 'RES' },
  ],
  processingTimeMs: 4015,
};

export const sampleInvoiceExtraction: InvoiceExtractionResult = {
  invoiceNumber: {
    key: 'invoiceNumber',
    label: 'Invoice Number',
    value: 'INV-2025-00847',
    confidence: 0.92,
  },
  invoiceDate: {
    key: 'invoiceDate',
    label: 'Invoice Date',
    value: '2025-01-15',
    confidence: 0.88,
  },
  dueDate: {
    key: 'dueDate',
    label: 'Due Date',
    value: '2025-02-14',
    confidence: 0.71,
  },
  issuerName: {
    key: 'issuerName',
    label: 'Issuer Name',
    value: 'Nexus Technology Solutions Ltd.',
    confidence: 0.74,
  },
  recipientName: {
    key: 'recipientName',
    label: 'Recipient Name',
    value: 'Arcadia Digital Ventures GmbH',
    confidence: 0.68,
  },
  totalAmount: {
    key: 'totalAmount',
    label: 'Total Amount',
    value: 'EUR 12,480.00',
    confidence: 0.85,
  },
};

export const pipelineSteps: PipelineStep[] = [
  {
    id: 'input',
    title: 'Document Input',
    description: 'A PDF or image is normalized into a consistent working page.',
    techniques: ['Parsing', 'Decoding', 'Normalization'],
    icon: 'IN',
    status: 'complete',
  },
  {
    id: 'preprocessing',
    title: 'Preprocessing',
    description: 'OCR, denoising, and layout cleanup make the document readable.',
    techniques: ['Tesseract OCR', 'Deskew', 'Cleanup'],
    icon: 'OCR',
    status: 'complete',
  },
  {
    id: 'features',
    title: 'Feature Extraction',
    description: 'TF-IDF bigrams, handcrafted image features, and text meta-features combine into a 798-dimensional vector.',
    techniques: ['TF-IDF bigrams', 'HOG + layout', 'Text meta-features'],
    icon: 'FX',
    status: 'complete',
  },
  {
    id: 'classification',
    title: 'Document Classification',
    description: 'A soft-voting ensemble (SVM-RBF + Logistic Regression + Random Forest) assigns one of four document classes.',
    techniques: ['Voting ensemble', 'SVM + LR + RF', 'StandardScaler'],
    icon: 'CLS',
    status: 'complete',
  },
  {
    id: 'extraction',
    title: 'Invoice Field Extraction',
    description: 'Invoices flow through image preprocessing and LayoutLM document-QA to recover 6 structured fields.',
    techniques: ['CLAHE preprocessing', 'LayoutLMv2', 'Document QA'],
    icon: 'NER',
    status: 'complete',
  },
];

export const sampleMetrics: MetricCard[] = [
  {
    label: 'Classification Accuracy',
    value: 93.8,
    suffix: '%',
    description: 'Weighted accuracy of the soft-voting ensemble across 4 document categories on the held-out validation set.',
    color: 'var(--color-accent-indigo)',
  },
  {
    label: 'Samples per Class',
    value: 200,
    suffix: '',
    description: 'Approximate balanced count per category in the RVL-CDIP small-200 subset, pre-split into training and held-out validation folds.',
    color: 'var(--color-accent-blue)',
  },
  {
    label: 'Invoice Fields Recovered',
    value: 6,
    suffix: '',
    description: 'Structured fields extracted per invoice by LayoutLM document-QA: invoice number, invoice date, due date, issuer name, recipient name, total amount.',
    color: 'var(--color-accent-emerald)',
  },
  {
    label: 'Avg. Processing Time',
    value: 6.5,
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
    confidence: 0.812,
    extraction: sampleInvoiceExtraction,
  },
  {
    id: 'cs2',
    documentName: 'jane_doe_resume.pdf',
    documentType: 'PDF - Resume',
    previewPlaceholder: 'RESUME',
    classifiedAs: 'resume',
    classifiedLabel: 'Resume',
    confidence: 0.961,
  },
  {
    id: 'cs3',
    documentName: 'attention_is_all_you_need.pdf',
    documentType: 'PDF - Scientific Publication',
    previewPlaceholder: 'PAPER',
    classifiedAs: 'scientific_publication',
    classifiedLabel: 'Scientific Publication',
    confidence: 0.752,
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
    id: 'sample_email',
    name: 'project_status_email.pdf',
    type: 'application/pdf',
    size: 142336,
    category: 'email',
    classification: sampleEmailClassification,
  },
  {
    id: 'sample_resume',
    name: 'jane_doe_resume.pdf',
    type: 'application/pdf',
    size: 198144,
    category: 'resume',
    classification: sampleResumeClassification,
  },
  {
    id: 'sample_scientific',
    name: 'transformer_paper_2017.pdf',
    type: 'application/pdf',
    size: 412288,
    category: 'scientific_publication',
    classification: sampleScientificClassification,
  },
];
