import { useCallback, useState } from 'react';
import type {
  AnalysisPhase,
  ClassificationResult,
  InvoiceExtractionResult,
  UploadedDocument,
} from '../types';
import { sampleDocuments, type SampleDocument } from '../data/sampleData';
import { delay, generateId } from '../utils/helpers';
import { isAuthenticated } from '../services/api';
import { uploadDocument, pollDocument, deleteDocument } from '../services/documents';

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

  const updateDoc = useCallback((id: string, updates: Partial<UploadedDocument>) => {
    setDocuments((prev) => prev.map((d) => (d.id === id ? { ...d, ...updates } : d)));
  }, []);

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
      setDocuments((prev) => {
        const idx = prev.findIndex((d) => d.id === id);
        const doc = prev[idx];

        // Fire-and-forget backend deletion if the file was already uploaded
        if (doc?.backendId) {
          deleteDocument(doc.backendId).catch(() => undefined);
        }

        const remaining = prev.filter((d) => d.id !== id);

        // Pick the nearest neighbour as the new active document
        setActiveDocumentId((curr) => {
          if (curr !== id) return curr;
          return remaining[idx]?.id ?? remaining[idx - 1]?.id ?? null;
        });

        return remaining;
      });
    },
    []
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

  // ── Mock analysis (sample documents / unauthenticated) ──────────────────────

  const simulateAnalysis = useCallback(
    async (
      doc: UploadedDocument
    ): Promise<{ classification: ClassificationResult; extraction?: InvoiceExtractionResult }> => {
      const sampleRef = (doc as UploadedDocumentWithSample)._sample;
      if (sampleRef) {
        return { classification: sampleRef.classification, extraction: sampleRef.extraction };
      }
      const random = sampleDocuments[Math.floor(Math.random() * sampleDocuments.length)];
      return { classification: random.classification, extraction: random.extraction };
    },
    []
  );

  const runMockAnalysis = useCallback(
    async (mockDocs: UploadedDocument[]) => {
      for (const doc of mockDocs) {
        if (doc.status !== 'idle') continue;
        updateDoc(doc.id, { status: 'uploading', progress: 0 });
        for (let p = 20; p <= 100; p += 20) {
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

      for (const doc of mockDocs) {
        if (doc.status === 'classified' || doc.status === 'extracted') continue;
        const result = await simulateAnalysis(doc);

        updateDoc(doc.id, { classification: result.classification, status: 'classified' });

        if (result.classification.predictedCategory === 'invoice' && result.extraction) {
          setPhase('extracting_invoice');
          await delay(500);
          updateDoc(doc.id, { extraction: result.extraction, status: 'extracted' });
        }
      }
    },
    [simulateAnalysis, updateDoc]
  );

  // ── Real API analysis (authenticated, real files) ───────────────────────────

  const runApiAnalysis = useCallback(
    async (realDocs: UploadedDocument[]) => {
      // 1. Upload all files
      const uploadResults: Array<{ localId: string; backendId: string }> = [];

      for (const doc of realDocs) {
        if (doc.status !== 'idle' || !doc.file) continue;

        updateDoc(doc.id, { status: 'uploading', progress: 0 });
        try {
          // Simulate upload progress while the fetch is in-flight
          let fakeProgress = 0;
          const progressInterval = setInterval(() => {
            fakeProgress = Math.min(fakeProgress + 15, 85);
            updateDoc(doc.id, { progress: fakeProgress });
          }, 200);

          const result = await uploadDocument(doc.file);
          clearInterval(progressInterval);

          updateDoc(doc.id, {
            backendId: result.backendId,
            status: 'processing',
            progress: 100,
          });
          uploadResults.push({ localId: doc.id, backendId: result.backendId });
        } catch (err) {
          updateDoc(doc.id, {
            status: 'error',
            error: err instanceof Error ? err.message : 'Upload failed.',
          });
        }
      }

      if (uploadResults.length === 0) return;

      // 2. Poll all uploaded documents concurrently
      setPhase('classifying');

      await Promise.all(
        uploadResults.map(({ localId, backendId }) =>
          pollDocument(
            backendId,
            (update) => {
              // Stream intermediate classification results as they arrive
              const partial: Partial<UploadedDocument> = {};
              if (update.classification) partial.classification = update.classification;
              if (Object.keys(partial).length > 0) updateDoc(localId, partial);
            }
          )
            .then((final) => {
              const isInvoice =
                final.classification?.predictedCategory === 'invoice' && !!final.extraction;

              updateDoc(localId, {
                status: final.status === 'done' ? (isInvoice ? 'extracted' : 'classified') : 'error',
                classification: final.classification,
                extraction: final.extraction,
                error: final.status === 'error' ? 'Analysis failed on the server.' : undefined,
              });
            })
            .catch((err) => {
              updateDoc(localId, {
                status: 'error',
                error: err instanceof Error ? err.message : 'Analysis failed.',
              });
            })
        )
      );
    },
    [updateDoc]
  );

  // ── analyzeAll ───────────────────────────────────────────────────────────────

  const analyzeAll = useCallback(async () => {
    const idle = documents.filter((d) => d.status === 'idle');
    if (idle.length === 0) return;

    setPhase('uploading');

    const realDocs = idle.filter((d) => d.file !== null);
    const mockDocs = idle.filter((d) => d.file === null);

    // Run both in sequence: real first, then mock (they can coexist in the queue)
    if (realDocs.length > 0 && isAuthenticated()) {
      await runApiAnalysis(realDocs);
    } else if (realDocs.length > 0) {
      // Not authenticated — fall back to simulation for real files too
      await runMockAnalysis(realDocs);
    }

    if (mockDocs.length > 0) {
      await runMockAnalysis(mockDocs);
    }

    setPhase('complete');
    setActiveDocumentId((curr) => {
      if (curr && documents.some((d) => d.id === curr)) return curr;
      return documents[0]?.id ?? null;
    });
  }, [documents, runApiAnalysis, runMockAnalysis]);

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
