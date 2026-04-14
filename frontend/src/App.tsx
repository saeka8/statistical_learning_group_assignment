import { ClassificationResults } from './components/sections/ClassificationResults';
import { HeroSection } from './components/sections/HeroSection';
import { InvoiceExtraction } from './components/sections/InvoiceExtraction';
import { PipelineSection } from './components/sections/PipelineSection';
import { UploadWorkspace } from './components/sections/UploadWorkspace';
import { Footer } from './components/layout/Footer';
import { Navbar } from './components/layout/Navbar';
import { useAnalysis } from './hooks/useAnalysis';
import styles from './App.module.css';

export default function App() {
  const {
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
  } = useAnalysis();

  const analyzedDocuments = documents
    .filter((doc) => !!doc.classification)
    .map((doc) => ({
      id: doc.id,
      name: doc.name,
      classification: doc.classification!,
    }));

  const showClassification = phase === 'complete' && !!activeDocument?.classification;
  const showExtraction =
    phase === 'complete' &&
    activeDocument?.classification?.predictedCategory === 'invoice' &&
    !!activeDocument?.extraction;

  return (
    <div className={styles.appShell}>
      <div className={styles.ambientGlow} aria-hidden="true" />
      <div className={styles.ambientGrid} aria-hidden="true" />
      <Navbar />
      <main className={styles.main}>
        <HeroSection />

        <UploadWorkspace
          documents={documents}
          phase={phase}
          activeDocumentId={activeDocumentId}
          onAddFiles={addFiles}
          onRemoveDocument={removeDocument}
          onLoadSample={loadSample}
          onAnalyze={analyzeAll}
          onReset={reset}
          onSetActive={setActiveDocument}
        />

        <ClassificationResults
          result={activeDocument?.classification ?? null}
          isVisible={showClassification}
          documents={analyzedDocuments}
          activeDocumentId={activeDocumentId}
          activeDocumentName={activeDocument?.name ?? ''}
          onSetActive={setActiveDocument}
        />

        <InvoiceExtraction
          result={activeDocument?.extraction ?? null}
          isVisible={showExtraction}
          activeDocumentName={activeDocument?.name ?? ''}
        />

        <PipelineSection />
      </main>
      <Footer />
    </div>
  );
}
