export type DocumentCategory =
  | 'invoice'
  | 'contract'
  | 'technical_report'
  | 'email'
  | 'receipt'
  | 'letter';

export interface CategoryScore {
  category: DocumentCategory;
  label: string;
  confidence: number;
  icon: string;
}

export interface ClassificationResult {
  predictedCategory: DocumentCategory;
  predictedLabel: string;
  scores: CategoryScore[];
  processingTimeMs: number;
}

export interface ExtractedField {
  key: string;
  label: string;
  value: string;
  confidence: number;
  boundingBox?: BoundingBox;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface InvoiceExtractionResult {
  invoiceNumber: ExtractedField;
  invoiceDate: ExtractedField;
  dueDate: ExtractedField;
  issuerName: ExtractedField;
  recipientName: ExtractedField;
  totalAmount: ExtractedField;
  additionalFields?: ExtractedField[];
}

export type UploadStatus = 'idle' | 'uploading' | 'processing' | 'classified' | 'extracted' | 'error';

export interface UploadedDocument {
  id: string;
  file: File | null;
  name: string;
  size: number;
  type: string;
  previewUrl?: string;
  status: UploadStatus;
  progress: number;
  classification?: ClassificationResult;
  extraction?: InvoiceExtractionResult;
  error?: string;
}

export interface PipelineStep {
  id: string;
  title: string;
  description: string;
  techniques: string[];
  icon: string;
  status: 'pending' | 'active' | 'complete';
}

export interface MetricCard {
  label: string;
  value: number;
  suffix: string;
  description: string;
  color: string;
}

export interface CaseStudy {
  id: string;
  documentName: string;
  documentType: string;
  previewPlaceholder: string;
  classifiedAs: DocumentCategory;
  classifiedLabel: string;
  confidence: number;
  extraction?: InvoiceExtractionResult;
}

export type AnalysisPhase =
  | 'idle'
  | 'uploading'
  | 'preprocessing'
  | 'extracting_features'
  | 'classifying'
  | 'extracting_invoice'
  | 'complete'
  | 'error';

export interface AnalysisState {
  phase: AnalysisPhase;
  documents: UploadedDocument[];
  activeDocumentId: string | null;
}
