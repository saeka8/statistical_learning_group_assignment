import { ClassificationResults } from './components/sections/ClassificationResults';
import { HeroSection } from './components/sections/HeroSection';
import { InvoiceExtraction } from './components/sections/InvoiceExtraction';
import { PipelineSection } from './components/sections/PipelineSection';
import { UploadWorkspace } from './components/sections/UploadWorkspace';
import { Footer } from './components/layout/Footer';
import { Navbar } from './components/layout/Navbar';
import { useAnalysis } from './hooks/useAnalysis';

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

  const showClassification = phase === 'complete' && !!activeDocument?.classification;
  const showExtraction =
    phase === 'complete' &&
    activeDocument?.classification?.predictedCategory === 'invoice' &&
    !!activeDocument?.extraction;

  return (
    <>
      <Navbar />
      <main>
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
        />

        <InvoiceExtraction
          result={activeDocument?.extraction ?? null}
          isVisible={showExtraction}
        />

        <PipelineSection />
      </main>
      <Footer />
    </>
  );
}
