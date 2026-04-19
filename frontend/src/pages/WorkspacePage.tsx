import { Link } from 'react-router-dom';
import { Container } from '../components/layout/Container';
import { Navbar } from '../components/layout/Navbar';
import { SectionReveal } from '../components/common/SectionReveal';
import { WorkspaceDetailsPanel } from '../components/workspace/WorkspaceDetailsPanel';
import { WorkspaceLibrary } from '../components/workspace/WorkspaceLibrary';
import { WorkspaceSummary } from '../components/workspace/WorkspaceSummary';
import { useWorkspace } from '../hooks/useWorkspace';
import styles from './WorkspacePage.module.css';

export function WorkspacePage() {
  const workspace = useWorkspace();

  return (
    <div className={styles.shell}>
      <div className={styles.ambientGlow} aria-hidden="true" />
      <div className={styles.ambientGrid} aria-hidden="true" />
      <Navbar />

      <main className={styles.main}>
        <Container size="wide">
          <SectionReveal>
            <section className={styles.hero} aria-labelledby="workspace-page-title">
              <Link to="/" className={styles.backLink} aria-label="Back to main menu">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Main menu
              </Link>
              <h1 id="workspace-page-title" className={styles.title}>
                Workspace
              </h1>
            </section>
          </SectionReveal>
        </Container>

        <Container size="wide">
          {workspace.error ? (
            <div className={styles.errorBanner} role="alert">
              {workspace.error}
            </div>
          ) : null}

          <WorkspaceSummary
            summary={workspace.summary}
            isLoading={workspace.isSummaryLoading}
          />

          <div className={styles.dashboardGrid}>
            <WorkspaceLibrary
              documents={workspace.documents}
              selectedDocumentId={workspace.selectedDocumentId}
              query={workspace.query}
              status={workspace.status}
              label={workspace.label}
              ordering={workspace.ordering}
              labelOptions={workspace.labelOptions}
              isLoading={workspace.isDocumentsLoading}
              onQueryChange={workspace.setQuery}
              onStatusChange={workspace.setStatus}
              onLabelChange={workspace.setLabel}
              onOrderingChange={workspace.setOrdering}
              onSelectDocument={workspace.selectDocument}
            />

            <WorkspaceDetailsPanel
              document={workspace.selectedDocument}
              isLoading={workspace.isDocumentLoading}
            />
          </div>
        </Container>
      </main>
    </div>
  );
}
