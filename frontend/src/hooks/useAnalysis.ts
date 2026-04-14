import { useCallback, useState } from 'react';
import type {
  AnalysisPhase,
  ClassificationResult,
  InvoiceExtractionResult,
  UploadedDocument,
} from '../types';
import { sampleDocuments, type SampleDocument } from '../data/sampleData';
import { delay, generateId } from '../utils/helpers';

interface UseAnalysisReturn {
  documents: UploadedDocument[];
  phase: AnalysisPhase;
  activeDocumentId: string | null;
  activeDocument: UploadedDocument | null;
  addFiles: (files: FileList | File[]) => void;
  removeDocument: (id: string) => void;
  loadSample: (sampleId: string) => void;
  analyzeAll: () => Promise<void>;
  reset: () => void;
  setActiveDocument: (id: string) => void;
}

type UploadedDocumentWithSample = UploadedDocument & { _sample?: SampleDocument };

export function useAnalysis(): UseAnalysisReturn {
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [phase, setPhase] = useState<AnalysisPhase>('idle');
  const [activeDocumentId, setActiveDocumentId] = useState<string | null>(null);

  const activeDocument = documents.find((d) => d.id === activeDocumentId) ?? null;

  const addFiles = useCallback((files: FileList | File[]) => {
    const newDocs: UploadedDocument[] = Array.from(files).map((file) => ({
      id: generateId(),
      file,
      name: file.name,
      size: file.size,
      type: file.type,
      status: 'idle',
      progress: 0,
    }));

    setDocuments((prev) => [...prev, ...newDocs]);

    if (newDocs.length > 0) {
      setActiveDocumentId(newDocs[0].id);
    }
  }, []);

  const removeDocument = useCallback(
    (id: string) => {
      const removedIndex = documents.findIndex((doc) => doc.id === id);
      const remaining = documents.filter((doc) => doc.id !== id);

      setDocuments(remaining);
      setActiveDocumentId((curr) => {
        if (curr !== id) return curr;

        return remaining[removedIndex]?.id ?? remaining[removedIndex - 1]?.id ?? null;
      });
    },
    [documents]
  );

  const loadSample = useCallback((sampleId: string) => {
    const sample = sampleDocuments.find((s) => s.id === sampleId);
    if (!sample) return;

    const doc: UploadedDocumentWithSample = {
      id: generateId(),
      file: null,
      name: sample.name,
      size: sample.size,
      type: sample.type,
      status: 'idle',
      progress: 0,
      _sample: sample,
    };

    setDocuments((prev) => [...prev, doc]);
    setActiveDocumentId(doc.id);
  }, []);

  const simulateAnalysis = useCallback(
    async (
      doc: UploadedDocument
    ): Promise<{
      classification: ClassificationResult;
      extraction?: InvoiceExtractionResult;
    }> => {
      const sampleRef = (doc as UploadedDocumentWithSample)._sample;
      if (sampleRef) {
        return {
          classification: sampleRef.classification,
          extraction: sampleRef.extraction,
        };
      }

      const random = sampleDocuments[Math.floor(Math.random() * sampleDocuments.length)];
      return {
        classification: random.classification,
        extraction: random.extraction,
      };
    },
    []
  );

  const updateDoc = useCallback((id: string, updates: Partial<UploadedDocument>) => {
    setDocuments((prev) => prev.map((d) => (d.id === id ? { ...d, ...updates } : d)));
  }, []);

  const analyzeAll = useCallback(async () => {
    if (documents.length === 0) return;

    setPhase('uploading');

    for (const doc of documents) {
      if (doc.status !== 'idle') continue;
      updateDoc(doc.id, { status: 'uploading', progress: 0 });
      for (let p = 0; p <= 100; p += 20) {
        await delay(60);
        updateDoc(doc.id, { progress: p });
      }
      updateDoc(doc.id, { status: 'processing', progress: 100 });
    }

    setPhase('preprocessing');
    await delay(500);

    setPhase('extracting_features');
    await delay(600);

    setPhase('classifying');
    await delay(700);

    for (const doc of documents) {
      if (doc.status === 'classified' || doc.status === 'extracted') continue;
      const result = await simulateAnalysis(doc);

      updateDoc(doc.id, {
        classification: result.classification,
        status: 'classified',
      });

      if (result.classification.predictedCategory === 'invoice' && result.extraction) {
        setPhase('extracting_invoice');
        await delay(500);
        updateDoc(doc.id, {
          extraction: result.extraction,
          status: 'extracted',
        });
      }
    }

    setPhase('complete');
    setActiveDocumentId((curr) => {
      if (curr && documents.some((doc) => doc.id === curr)) return curr;
      return documents[0]?.id ?? null;
    });
  }, [documents, simulateAnalysis, updateDoc]);

  const reset = useCallback(() => {
    setDocuments([]);
    setPhase('idle');
    setActiveDocumentId(null);
  }, []);

  const setActiveDocument = useCallback((id: string) => {
    setActiveDocumentId(id);
  }, []);

  return {
    documents,
    phase,
    activeDocumentId,
    activeDocument,
    addFiles,
    removeDocument,
    loadSample,
    analyzeAll,
    reset,
    setActiveDocument,
  };
}
