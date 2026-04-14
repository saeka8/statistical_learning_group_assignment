import { Badge } from '../components/common/Badge';
import { Container } from '../components/layout/Container';
import { Navbar } from '../components/layout/Navbar';
import { SectionReveal } from '../components/common/SectionReveal';
import { WorkspaceDetailsPanel } from '../components/workspace/WorkspaceDetailsPanel';
import { WorkspaceLibrary } from '../components/workspace/WorkspaceLibrary';
import { WorkspaceSummary } from '../components/workspace/WorkspaceSummary';
import { useAuth } from '../hooks/useAuth';
import { useWorkspace } from '../hooks/useWorkspace';
import {
  deleteDocument,
  downloadDocument,
  rerunDocumentAnalysis,
} from '../services/documents';
import { getUserFacingError } from '../services/errorMessages';
import { useEffect, useState } from 'react';
import styles from './WorkspacePage.module.css';

export function WorkspacePage() {
  const { user } = useAuth();
  const workspace = useWorkspace();
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<'download' | 'rerun' | 'delete' | null>(null);

  useEffect(() => {
    setActionError(null);
  }, [workspace.selectedDocumentId]);

  const handleDownload = async () => {
    if (!workspace.selectedDocumentId) return;

    setActionLoading('download');
    try {
      const url = await downloadDocument(workspace.selectedDocumentId);
      window.open(url, '_blank', 'noopener,noreferrer');
      setActionError(null);
    } catch (error) {
      setActionError(
        getUserFacingError(error, 'workspaceDownload', 'We could not download that document.')
      );
    } finally {
      setActionLoading(null);
    }
  };

  const handleRerunAnalysis = async () => {
    if (!workspace.selectedDocumentId) return;

    setActionLoading('rerun');
    try {
      await rerunDocumentAnalysis(workspace.selectedDocumentId);
      workspace.reload();
      setActionError(null);
    } catch (error) {
      setActionError(
        getUserFacingError(error, 'workspaceRerun', 'We could not re-run analysis.')
      );
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async () => {
    if (!workspace.selectedDocumentId) return;

    setActionLoading('delete');
    try {
      await deleteDocument(workspace.selectedDocumentId);
      workspace.reload();
      setActionError(null);
    } catch (error) {
      setActionError(
        getUserFacingError(error, 'workspaceDelete', 'We could not delete that document.')
      );
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className={styles.shell}>
      <div className={styles.ambientGlow} aria-hidden="true" />
      <div className={styles.ambientGrid} aria-hidden="true" />
      <Navbar />

      <main className={styles.main}>
        <Container size="wide">
          <SectionReveal>
            <section className={styles.hero} aria-labelledby="workspace-page-title">
              <Badge label="Private workspace" variant="accent" />
              <h1 id="workspace-page-title" className={styles.title}>
                Workspace
              </h1>
              <p className={styles.subtitle}>
                {user?.displayName ? `${user.displayName}, ` : ''}
                track uploads, filter the library, and open the latest classification or invoice
                details without leaving the dashboard.
              </p>
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
            displayName={user?.displayName}
          />

          {actionError ? (
            <div className={styles.errorBanner} role="alert">
              {actionError}
            </div>
          ) : null}

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
              actionLoading={actionLoading}
              onDownload={handleDownload}
              onRerunAnalysis={handleRerunAnalysis}
              onDelete={handleDelete}
            />
          </div>
        </Container>
      </main>
    </div>
  );
}
