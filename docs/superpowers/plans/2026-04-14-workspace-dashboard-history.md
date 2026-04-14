# Workspace Dashboard History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a protected `/workspace` page with persistent document history, client-facing account statistics, document management actions, and clearer user-facing errors across auth, upload, analysis, and workspace flows.

**Architecture:** Promote auth into a shared React context, split the frontend into route-based pages, and protect a new `/workspace` route with a small router shell. Extend the Django documents app with one workspace summary endpoint plus richer document list filtering/sorting, then build the workspace UI on top of those APIs with a shared error-normalization layer.

**Tech Stack:** React 19, TypeScript, Vite, Motion, React Router, Playwright, Django REST Framework, Django ORM, pytest, Docker Compose

---

## File Structure

- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/hooks/useAuth.ts`
- Modify: `frontend/src/components/layout/Navbar.tsx`
- Modify: `frontend/src/components/layout/Navbar.module.css`
- Modify: `frontend/src/components/layout/AuthDialog.tsx`
- Modify: `frontend/src/components/sections/MetricsSection.tsx`
- Modify: `frontend/src/hooks/useAnalysis.ts`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/services/documents.ts`
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/context/AuthContext.tsx`
- Create: `frontend/src/components/routing/ProtectedRoute.tsx`
- Create: `frontend/src/pages/LandingPage.tsx`
- Create: `frontend/src/pages/WorkspacePage.tsx`
- Create: `frontend/src/pages/WorkspacePage.module.css`
- Create: `frontend/src/components/workspace/WorkspaceSummary.tsx`
- Create: `frontend/src/components/workspace/WorkspaceSummary.module.css`
- Create: `frontend/src/components/workspace/WorkspaceLibrary.tsx`
- Create: `frontend/src/components/workspace/WorkspaceLibrary.module.css`
- Create: `frontend/src/components/workspace/WorkspaceDetailsPanel.tsx`
- Create: `frontend/src/components/workspace/WorkspaceDetailsPanel.module.css`
- Create: `frontend/src/hooks/useWorkspace.ts`
- Create: `frontend/src/services/workspace.ts`
- Create: `frontend/src/services/errorMessages.ts`
- Modify: `backend/apps/documents/filters.py`
- Modify: `backend/apps/documents/serializers.py`
- Modify: `backend/apps/documents/views.py`
- Modify: `backend/apps/documents/urls.py`
- Create: `backend/apps/documents/tests/__init__.py`
- Create: `backend/apps/documents/tests/test_workspace_api.py`
- Create: `frontend/tests/workspace-route.spec.ts`
- Create: `frontend/tests/workspace-library.spec.ts`
- Create: `frontend/tests/workspace-actions.spec.ts`

### Task 1: Add routing, shared auth, and a protected workspace shell

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/hooks/useAuth.ts`
- Modify: `frontend/src/components/sections/MetricsSection.tsx`
- Create: `frontend/src/context/AuthContext.tsx`
- Create: `frontend/src/components/routing/ProtectedRoute.tsx`
- Create: `frontend/src/pages/LandingPage.tsx`
- Create: `frontend/src/pages/WorkspacePage.tsx`
- Test: `frontend/tests/workspace-route.spec.ts`

- [ ] **Step 1: Write the failing route-protection test**

```ts
import { expect, test } from '@playwright/test';

test('guests are redirected away from the workspace route', async ({ page }) => {
  await page.goto('/workspace');

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('button', { name: /^log in$/i })).toBeVisible();
});

test('authenticated users can open the protected workspace route', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('auth_access', 'test-access');
    localStorage.setItem('auth_refresh', 'test-refresh');
  });

  await page.route('**/api/profile/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          id: 7,
          username: 'vako',
          email: 'vako@example.com',
          profile: {
            display_name: 'Vako',
            avatar_url: '',
            created_at: '2026-04-14T11:00:00Z',
          },
        },
      }),
    });
  });

  await page.route('**/api/workspace/summary/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          totals: {
            uploads: 0,
            processed: 0,
            errors: 0,
            invoices: 0,
          },
          dominant_label: null,
          recent_invoice_total: null,
          recent_activity: [],
        },
      }),
    });
  });

  await page.route('**/api/documents/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          count: 0,
          next: null,
          previous: null,
          results: [],
        },
      }),
    });
  });

  await page.goto('/workspace');

  await expect(page).toHaveURL(/\/workspace$/);
  await expect(page.getByRole('heading', { name: /workspace/i })).toBeVisible();
});
```

- [ ] **Step 2: Run the route test to verify it fails**

Run from `frontend/`:

```powershell
node .\node_modules\@playwright\test\cli.js test tests/workspace-route.spec.ts --config playwright.config.ts
```

Expected: FAIL because the app has no `/workspace` route and no shared auth guard yet.

- [ ] **Step 3: Implement the minimal routed app shell and shared auth context**

Update `frontend/package.json` to add the router dependency:

```json
{
  "dependencies": {
    "@react-three/drei": "^10.7.6",
    "@react-three/fiber": "^9.4.0",
    "motion": "^12.23.24",
    "react": "^19.2.4",
    "react-dom": "^19.2.4",
    "react-router-dom": "^7.9.6",
    "three": "^0.181.1"
  }
}
```

Install it from `frontend/`:

```powershell
npm install
```

Create `frontend/src/context/AuthContext.tsx`:

```tsx
import { createContext, useCallback, useEffect, useMemo, useState } from 'react';
import * as authService from '../services/auth';
import { clearTokens, isAuthenticated as hasToken } from '../services/api';

export interface AuthUser {
  username: string;
  displayName: string;
  email: string;
  initials: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

function buildInitials(displayName: string): string {
  const tokens = displayName.trim().split(/\s+/).filter(Boolean);
  if (tokens.length === 0) return 'U';
  if (tokens.length === 1) return tokens[0].slice(0, 2).toUpperCase();
  return `${tokens[0][0]}${tokens[1][0]}`.toUpperCase();
}

function toAuthUser(profile: authService.UserProfile): AuthUser {
  return {
    ...profile,
    initials: buildInitials(profile.displayName),
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!hasToken()) {
      setLoading(false);
      return;
    }

    authService
      .getProfile()
      .then((profile) => setUser(toAuthUser(profile)))
      .catch(() => {
        clearTokens();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const profile = await authService.login(username, password);
    setUser(toAuthUser(profile));
  }, []);

  const register = useCallback(async (username: string, email: string, password: string, displayName?: string) => {
    const profile = await authService.register(username, email, password, displayName);
    setUser(toAuthUser(profile));
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: !!user,
      loading,
      login,
      register,
      logout,
    }),
    [user, loading, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
```

Replace `frontend/src/hooks/useAuth.ts` with a context-backed hook:

```ts
import { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider.');
  }
  return context;
}
```

Create `frontend/src/components/routing/ProtectedRoute.tsx`:

```tsx
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div aria-label="Loading workspace">Loading workspace...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace state={{ authIntent: 'login', from: location.pathname }} />;
  }

  return <>{children}</>;
}
```

Create `frontend/src/pages/LandingPage.tsx`:

```tsx
import { ClassificationResults } from '../components/sections/ClassificationResults';
import { HeroSection } from '../components/sections/HeroSection';
import { InvoiceExtraction } from '../components/sections/InvoiceExtraction';
import { PipelineSection } from '../components/sections/PipelineSection';
import { UploadWorkspace } from '../components/sections/UploadWorkspace';
import { Footer } from '../components/layout/Footer';
import { Navbar } from '../components/layout/Navbar';
import { useAnalysis } from '../hooks/useAnalysis';
import styles from '../App.module.css';

export function LandingPage() {
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
```

Create an initial `frontend/src/pages/WorkspacePage.tsx` shell:

```tsx
export function WorkspacePage() {
  return (
    <main>
      <h1>Workspace</h1>
      <p>Your private document workspace is loading.</p>
    </main>
  );
}
```

Replace `frontend/src/App.tsx` with the route shell:

```tsx
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/routing/ProtectedRoute';
import { LandingPage } from './pages/LandingPage';
import { WorkspacePage } from './pages/WorkspacePage';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route
            path="/workspace"
            element={
              <ProtectedRoute>
                <WorkspacePage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
```

Fix the broken closing tags in `frontend/src/components/sections/MetricsSection.tsx`:

```tsx
        <SectionReveal delay={0.4}>
          <div className={styles.miniStats}>
            <div className={styles.miniStat}>
              <span className={styles.miniValue}>4</span>
              <span className={styles.miniLabel}>Document Categories</span>
            </div>
            <div className={styles.miniDivider} aria-hidden="true" />
            <div className={styles.miniStat}>
              <span className={styles.miniValue}>400</span>
              <span className={styles.miniLabel}>Training Samples</span>
            </div>
            <div className={styles.miniDivider} aria-hidden="true" />
            <div className={styles.miniStat}>
              <span className={styles.miniValue}>533</span>
              <span className={styles.miniLabel}>Hybrid Features</span>
            </div>
            <div className={styles.miniDivider} aria-hidden="true" />
            <div className={styles.miniStat}>
              <span className={styles.miniValue}>GridSearchCV</span>
              <span className={styles.miniLabel}>Hyperparameter Tuning</span>
            </div>
          </div>
        </SectionReveal>
      </Container>
    </section>
  );
}
```

- [ ] **Step 4: Run the route test and a build to verify the shell works**

Run from `frontend/`:

```powershell
node .\node_modules\@playwright\test\cli.js test tests/workspace-route.spec.ts --config playwright.config.ts
npm.cmd run build
```

Expected:
- Playwright PASS for both route tests
- TypeScript/Vite build PASS

- [ ] **Step 5: Commit**

```powershell
git add frontend/package.json frontend/package-lock.json frontend/src/App.tsx frontend/src/main.tsx frontend/src/hooks/useAuth.ts frontend/src/context/AuthContext.tsx frontend/src/components/routing/ProtectedRoute.tsx frontend/src/pages/LandingPage.tsx frontend/src/pages/WorkspacePage.tsx frontend/src/components/sections/MetricsSection.tsx frontend/tests/workspace-route.spec.ts
git commit -m "feat: add protected workspace routing shell"
```

### Task 2: Add the backend workspace summary endpoint and richer document queries

**Files:**
- Modify: `backend/apps/documents/filters.py`
- Modify: `backend/apps/documents/serializers.py`
- Modify: `backend/apps/documents/views.py`
- Modify: `backend/apps/documents/urls.py`
- Create: `backend/apps/documents/tests/__init__.py`
- Create: `backend/apps/documents/tests/test_workspace_api.py`

- [ ] **Step 1: Write the failing backend API tests**

Create `backend/apps/documents/tests/test_workspace_api.py`:

```python
from decimal import Decimal
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.documents.models import ClassificationResult, Document, DocumentStatus, InvoiceExtraction


def make_document(owner, filename, status, label=None, confidence=0.0, total_amount=None):
    document = Document.objects.create(
        owner=owner,
        filename=filename,
        content_type="application/pdf",
        file_size=2048,
        storage_key=f"{owner.pk}/{filename}",
        status=status,
    )
    if label:
        ClassificationResult.objects.create(
            document=document,
            predicted_label=label,
            confidence=confidence,
            all_scores={label: confidence},
            model_version="test-model",
        )
    if total_amount is not None:
        InvoiceExtraction.objects.create(
            document=document,
            invoice_number="INV-1",
            issuer_name="Issuer",
            recipient_name="Recipient",
            total_amount=Decimal(total_amount),
            currency="EUR",
            raw_text="invoice",
            confidence_map={"total_amount": 0.95},
        )
    return document


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_workspace_summary_returns_practical_stats(db):
    user = User.objects.create_user(username="vako", password="secret123")
    other = User.objects.create_user(username="other", password="secret123")

    make_document(user, "invoice-a.pdf", DocumentStatus.DONE, "invoice", 0.96, "125.50")
    make_document(user, "invoice-b.pdf", DocumentStatus.ERROR, "invoice", 0.62, "80.00")
    make_document(user, "resume.pdf", DocumentStatus.DONE, "resume", 0.88)
    make_document(other, "other.pdf", DocumentStatus.DONE, "email", 0.99)

    response = auth_client(user).get("/api/workspace/summary/")

    assert response.status_code == 200
    payload = response.data["data"]
    assert payload["totals"] == {
        "uploads": 3,
        "processed": 2,
        "errors": 1,
        "invoices": 2,
    }
    assert payload["dominant_label"]["value"] == "invoice"
    assert payload["recent_invoice_total"] == "205.50"
    assert len(payload["recent_activity"]) == 3


def test_document_list_supports_search_filters_and_confidence_sorting(db):
    user = User.objects.create_user(username="vako", password="secret123")
    make_document(user, "invoice-a.pdf", DocumentStatus.DONE, "invoice", 0.64)
    make_document(user, "invoice-b.pdf", DocumentStatus.DONE, "invoice", 0.97)
    make_document(user, "resume.pdf", DocumentStatus.ERROR, "resume", 0.81)

    client = auth_client(user)

    response = client.get("/api/documents/?q=invoice&label=invoice&ordering=confidence")

    assert response.status_code == 200
    results = response.data["data"]["results"]
    assert [item["filename"] for item in results] == ["invoice-b.pdf", "invoice-a.pdf"]

    error_response = client.get("/api/documents/?status=error")
    error_results = error_response.data["data"]["results"]
    assert [item["filename"] for item in error_results] == ["resume.pdf"]
```

- [ ] **Step 2: Run the backend tests to verify they fail**

Run from the repo root while Docker is up:

```powershell
docker compose exec api python -m pytest apps/documents/tests/test_workspace_api.py -v
```

Expected: FAIL because `/api/workspace/summary/` does not exist and the document list does not support `q` or `ordering=confidence`.

- [ ] **Step 3: Implement the summary endpoint and document query extensions**

Extend `backend/apps/documents/filters.py`:

```python
from django.db.models import F

from .models import DocumentCategory, DocumentStatus


def apply_document_filters(queryset, request):
    status = request.query_params.get("status")
    label = request.query_params.get("label")
    query = request.query_params.get("q")
    ordering = request.query_params.get("ordering", "newest")

    if status and status in DocumentStatus.values:
      queryset = queryset.filter(status=status)

    if label and label in DocumentCategory.values:
      queryset = queryset.filter(classification__predicted_label=label)

    if query:
      queryset = queryset.filter(filename__icontains=query.strip())

    if ordering == "oldest":
      queryset = queryset.order_by("created_at")
    elif ordering == "confidence":
      queryset = queryset.order_by(F("classification__confidence").desc(nulls_last=True), "-created_at")
    else:
      queryset = queryset.order_by("-created_at")

    return queryset
```

Add summary serializers in `backend/apps/documents/serializers.py`:

```python
class WorkspaceActivitySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    filename = serializers.CharField()
    status = serializers.CharField()
    label = serializers.CharField(allow_null=True)
    confidence = serializers.FloatField(allow_null=True)
    created_at = serializers.DateTimeField()


class WorkspaceSummarySerializer(serializers.Serializer):
    totals = serializers.DictField(child=serializers.IntegerField())
    dominant_label = serializers.DictField(allow_null=True)
    recent_invoice_total = serializers.CharField(allow_null=True)
    recent_activity = WorkspaceActivitySerializer(many=True)
```

Expand `DocumentListSerializer` so the workspace library can render useful metadata:

```python
class DocumentListSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    confidence = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "filename",
            "content_type",
            "file_size",
            "status",
            "label",
            "confidence",
            "created_at",
            "updated_at",
        ]
```

Add a `WorkspaceSummaryView` in `backend/apps/documents/views.py`:

```python
from django.db.models import Count, Sum


class WorkspaceSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = Document.objects.filter(owner=request.user).select_related(
            "classification",
            "invoice_data",
        )

        totals = {
            "uploads": queryset.count(),
            "processed": queryset.filter(status=DocumentStatus.DONE).count(),
            "errors": queryset.filter(status=DocumentStatus.ERROR).count(),
            "invoices": queryset.filter(classification__predicted_label="invoice").count(),
        }

        dominant = (
            queryset.filter(classification__isnull=False)
            .values("classification__predicted_label")
            .annotate(total=Count("id"))
            .order_by("-total")
            .first()
        )
        dominant_label = None
        if dominant:
            dominant_label = {
                "value": dominant["classification__predicted_label"],
                "count": dominant["total"],
            }

        invoice_total = (
            queryset.filter(invoice_data__total_amount__isnull=False)
            .aggregate(total=Sum("invoice_data__total_amount"))
            .get("total")
        )

        recent_activity = [
            {
                "id": doc.id,
                "filename": doc.filename,
                "status": doc.status,
                "label": getattr(getattr(doc, "classification", None), "predicted_label", None),
                "confidence": getattr(getattr(doc, "classification", None), "confidence", None),
                "created_at": doc.created_at,
            }
            for doc in queryset[:5]
        ]

        serializer = WorkspaceSummarySerializer(
            {
                "totals": totals,
                "dominant_label": dominant_label,
                "recent_invoice_total": str(invoice_total) if invoice_total is not None else None,
                "recent_activity": recent_activity,
            }
        )
        return Response(serializer.data)
```

Register the endpoint in `backend/apps/documents/urls.py`:

```python
from .views import WorkspaceSummaryView

urlpatterns = [
    path("workspace/summary/", WorkspaceSummaryView.as_view(), name="workspace-summary"),
    path("documents/", DocumentListCreateView.as_view(), name="document-list"),
    path("documents/<uuid:id>/", DocumentDetailView.as_view(), name="document-detail"),
    path("documents/<uuid:id>/download/", DocumentDownloadView.as_view(), name="document-download"),
    path("documents/<uuid:id>/classify/", ClassifyView.as_view(), name="document-classify"),
    path("documents/<uuid:id>/classify/status/", ClassifyStatusView.as_view(), name="document-classify-status"),
    path("documents/<uuid:id>/extraction/", ExtractionView.as_view(), name="document-extraction"),
]
```

- [ ] **Step 4: Run the backend tests to verify they pass**

Run from the repo root:

```powershell
docker compose exec api python -m pytest apps/documents/tests/test_workspace_api.py -v
```

Expected: PASS for both tests.

- [ ] **Step 5: Commit**

```powershell
git add backend/apps/documents/filters.py backend/apps/documents/serializers.py backend/apps/documents/views.py backend/apps/documents/urls.py backend/apps/documents/tests/__init__.py backend/apps/documents/tests/test_workspace_api.py
git commit -m "feat: add workspace summary api"
```

### Task 3: Build the workspace data layer, page layout, and navigation entry points

**Files:**
- Modify: `frontend/src/components/layout/Navbar.tsx`
- Modify: `frontend/src/components/layout/Navbar.module.css`
- Modify: `frontend/src/services/documents.ts`
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/services/workspace.ts`
- Create: `frontend/src/hooks/useWorkspace.ts`
- Create: `frontend/src/pages/WorkspacePage.tsx`
- Create: `frontend/src/pages/WorkspacePage.module.css`
- Create: `frontend/src/components/workspace/WorkspaceSummary.tsx`
- Create: `frontend/src/components/workspace/WorkspaceSummary.module.css`
- Create: `frontend/src/components/workspace/WorkspaceLibrary.tsx`
- Create: `frontend/src/components/workspace/WorkspaceLibrary.module.css`
- Create: `frontend/src/components/workspace/WorkspaceDetailsPanel.tsx`
- Create: `frontend/src/components/workspace/WorkspaceDetailsPanel.module.css`
- Test: `frontend/tests/workspace-library.spec.ts`

- [ ] **Step 1: Write the failing workspace UI test**

Create `frontend/tests/workspace-library.spec.ts`:

```ts
import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('auth_access', 'workspace-access');
    localStorage.setItem('auth_refresh', 'workspace-refresh');
  });

  await page.route('**/api/profile/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          id: 3,
          username: 'vako',
          email: 'vako@example.com',
          profile: {
            display_name: 'Vako',
            avatar_url: '',
            created_at: '2026-04-14T11:00:00Z',
          },
        },
      }),
    });
  });

  await page.route('**/api/workspace/summary/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          totals: {
            uploads: 4,
            processed: 3,
            errors: 1,
            invoices: 2,
          },
          dominant_label: {
            value: 'invoice',
            count: 2,
          },
          recent_invoice_total: '205.50',
          recent_activity: [],
        },
      }),
    });
  });

  await page.route('**/api/documents/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          count: 2,
          next: null,
          previous: null,
          results: [
            {
              id: 'c0f4e5c4-2a2f-4544-9cd7-3a69a4158f11',
              filename: 'invoice-b.pdf',
              content_type: 'application/pdf',
              file_size: 1200,
              status: 'done',
              label: 'invoice',
              confidence: 0.97,
              created_at: '2026-04-14T12:00:00Z',
              updated_at: '2026-04-14T12:05:00Z',
            },
            {
              id: 'a05f75c0-2112-49db-8b96-85784f7f48c1',
              filename: 'resume.pdf',
              content_type: 'application/pdf',
              file_size: 950,
              status: 'error',
              label: 'resume',
              confidence: 0.81,
              created_at: '2026-04-14T10:00:00Z',
              updated_at: '2026-04-14T10:03:00Z',
            },
          ],
        },
      }),
    });
  });

  await page.route('**/api/documents/c0f4e5c4-2a2f-4544-9cd7-3a69a4158f11/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          id: 'c0f4e5c4-2a2f-4544-9cd7-3a69a4158f11',
          filename: 'invoice-b.pdf',
          content_type: 'application/pdf',
          file_size: 1200,
          status: 'done',
          created_at: '2026-04-14T12:00:00Z',
          updated_at: '2026-04-14T12:05:00Z',
          classification: {
            predicted_label: 'invoice',
            confidence: 0.97,
            all_scores: { invoice: 0.97, email: 0.02 },
            model_version: 'test-model',
            classified_at: '2026-04-14T12:05:00Z',
          },
          invoice_data: {
            invoice_number: 'INV-22',
            invoice_date: '2026-04-01',
            due_date: '2026-04-30',
            issuer_name: 'Northwind',
            recipient_name: 'DocLens',
            total_amount: '205.50',
            currency: 'EUR',
            confidence_map: { total_amount: 0.96 },
            extracted_at: '2026-04-14T12:05:00Z',
          },
        },
      }),
    });
  });
});

test('workspace shows account stats, searchable history, and document details', async ({ page }) => {
  await page.goto('/workspace');

  await expect(page.getByRole('heading', { name: /workspace/i })).toBeVisible();
  await expect(page.getByText('Total uploads')).toBeVisible();
  await expect(page.getByText('205.50')).toBeVisible();
  await expect(page.getByText('invoice-b.pdf')).toBeVisible();

  await page.getByPlaceholder(/search documents/i).fill('invoice');
  await expect(page.getByText('resume.pdf')).toHaveCount(0);

  await page.getByRole('button', { name: /view details for invoice-b.pdf/i }).click();
  await expect(page.getByText('INV-22')).toBeVisible();
  await expect(page.getByText('Northwind')).toBeVisible();
});
```

- [ ] **Step 2: Run the workspace UI test to verify it fails**

Run from `frontend/`:

```powershell
node .\node_modules\@playwright\test\cli.js test tests/workspace-library.spec.ts --config playwright.config.ts
```

Expected: FAIL because the workspace page is still only a loading shell and the navbar has no workspace entry.

- [ ] **Step 3: Implement the workspace types, API helpers, hook, and UI**

Extend `frontend/src/types/index.ts` with workspace-specific shapes:

```ts
export interface WorkspaceTotals {
  uploads: number;
  processed: number;
  errors: number;
  invoices: number;
}

export interface WorkspaceActivityItem {
  id: string;
  filename: string;
  status: 'pending' | 'processing' | 'done' | 'error';
  label: string | null;
  confidence: number | null;
  createdAt: string;
}

export interface WorkspaceSummaryData {
  totals: WorkspaceTotals;
  dominantLabel: { value: string; count: number } | null;
  recentInvoiceTotal: string | null;
  recentActivity: WorkspaceActivityItem[];
}

export interface WorkspaceDocumentListItem {
  id: string;
  filename: string;
  contentType: string;
  fileSize: number;
  status: 'pending' | 'processing' | 'done' | 'error';
  label: string | null;
  confidence: number | null;
  createdAt: string;
  updatedAt: string;
}
```

Create `frontend/src/services/workspace.ts`:

```ts
import { api } from './api';
import type { WorkspaceDocumentListItem, WorkspaceSummaryData } from '../types';

interface WorkspaceSummaryResponse {
  totals: {
    uploads: number;
    processed: number;
    errors: number;
    invoices: number;
  };
  dominant_label: { value: string; count: number } | null;
  recent_invoice_total: string | null;
  recent_activity: Array<{
    id: string;
    filename: string;
    status: 'pending' | 'processing' | 'done' | 'error';
    label: string | null;
    confidence: number | null;
    created_at: string;
  }>;
}

interface BackendDocumentListItem {
  id: string;
  filename: string;
  content_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'done' | 'error';
  label: string | null;
  confidence: number | null;
  created_at: string;
  updated_at: string;
}

interface PaginatedDocuments {
  count: number;
  next: string | null;
  previous: string | null;
  results: BackendDocumentListItem[];
}

export async function getWorkspaceSummary(): Promise<WorkspaceSummaryData> {
  const data = await api.get<WorkspaceSummaryResponse>('/workspace/summary/');
  return {
    totals: data.totals,
    dominantLabel: data.dominant_label,
    recentInvoiceTotal: data.recent_invoice_total,
    recentActivity: data.recent_activity.map((item) => ({
      id: item.id,
      filename: item.filename,
      status: item.status,
      label: item.label,
      confidence: item.confidence,
      createdAt: item.created_at,
    })),
  };
}

export async function listWorkspaceDocuments(query: string, status: string, label: string, ordering: string) {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  if (status && status !== 'all') params.set('status', status);
  if (label && label !== 'all') params.set('label', label);
  if (ordering) params.set('ordering', ordering);

  const data = await api.get<PaginatedDocuments>(`/documents/?${params.toString()}`);
  return {
    count: data.count,
    items: data.results.map<WorkspaceDocumentListItem>((item) => ({
      id: item.id,
      filename: item.filename,
      contentType: item.content_type,
      fileSize: item.file_size,
      status: item.status,
      label: item.label,
      confidence: item.confidence,
      createdAt: item.created_at,
      updatedAt: item.updated_at,
    })),
  };
}
```

Create `frontend/src/hooks/useWorkspace.ts`:

```ts
import { useEffect, useState } from 'react';
import { getDocument } from '../services/documents';
import { getWorkspaceSummary, listWorkspaceDocuments } from '../services/workspace';
import type { DocumentResult } from '../services/documents';
import type { WorkspaceDocumentListItem, WorkspaceSummaryData } from '../types';

export function useWorkspace() {
  const [summary, setSummary] = useState<WorkspaceSummaryData | null>(null);
  const [documents, setDocuments] = useState<WorkspaceDocumentListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<DocumentResult | null>(null);
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [labelFilter, setLabelFilter] = useState('all');
  const [ordering, setOrdering] = useState('newest');
  const [loading, setLoading] = useState(true);

  const loadWorkspace = () => {
    setLoading(true);
    Promise.all([
      getWorkspaceSummary(),
      listWorkspaceDocuments(query, statusFilter, labelFilter, ordering),
    ])
      .then(([summaryData, listData]) => {
        setSummary(summaryData);
        setDocuments(listData.items);
        setSelectedId((current) => current ?? listData.items[0]?.id ?? null);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadWorkspace();
  }, [query, statusFilter, labelFilter, ordering]);

  useEffect(() => {
    if (!selectedId) {
      setSelectedDocument(null);
      return;
    }
    getDocument(selectedId).then(setSelectedDocument);
  }, [selectedId]);

  return {
    summary,
    documents,
    selectedId,
    selectedDocument,
    loading,
    query,
    statusFilter,
    labelFilter,
    ordering,
    setQuery,
    setStatusFilter,
    setLabelFilter,
    setOrdering,
    setSelectedId,
    reload: loadWorkspace,
  };
}
```

Update `frontend/src/services/documents.ts` so `DocumentResult` keeps detail timestamps:

```ts
export interface DocumentResult {
  backendId: string;
  filename: string;
  status: BackendDocument['status'];
  createdAt?: string;
  updatedAt?: string;
  classification: ClassificationResult | undefined;
  extraction: InvoiceExtractionResult | undefined;
}

function mapDocument(d: BackendDocument): DocumentResult {
  return {
    backendId: d.id,
    filename: d.filename,
    status: d.status,
    createdAt: d.created_at,
    updatedAt: d.updated_at,
    classification: d.classification ? mapClassification(d.classification) : undefined,
    extraction: d.invoice_data ? mapExtraction(d.invoice_data) : undefined,
  };
}
```

Create `frontend/src/components/workspace/WorkspaceSummary.tsx`:

```tsx
import type { WorkspaceSummaryData } from '../../types';
import styles from './WorkspaceSummary.module.css';

export function WorkspaceSummary({ summary, displayName }: { summary: WorkspaceSummaryData; displayName: string }) {
  return (
    <section className={styles.section}>
      <div className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Private workspace</p>
          <h1 className={styles.title}>Workspace</h1>
          <p className={styles.copy}>{displayName}, here is the live history of your uploaded documents.</p>
        </div>
      </div>
      <div className={styles.cardGrid}>
        <article className={styles.card}><span>Total uploads</span><strong>{summary.totals.uploads}</strong></article>
        <article className={styles.card}><span>Processed successfully</span><strong>{summary.totals.processed}</strong></article>
        <article className={styles.card}><span>Invoices detected</span><strong>{summary.totals.invoices}</strong></article>
        <article className={styles.card}><span>Most common type</span><strong>{summary.dominantLabel?.value ?? 'None yet'}</strong></article>
      </div>
      {summary.recentInvoiceTotal ? <p className={styles.invoiceTotal}>Recent invoice total: {summary.recentInvoiceTotal}</p> : null}
    </section>
  );
}
```

Create `frontend/src/components/workspace/WorkspaceLibrary.tsx`:

```tsx
import { formatFileSize } from '../../utils/helpers';
import type { WorkspaceDocumentListItem } from '../../types';
import styles from './WorkspaceLibrary.module.css';

interface WorkspaceLibraryProps {
  documents: WorkspaceDocumentListItem[];
  selectedId: string | null;
  query: string;
  statusFilter: string;
  labelFilter: string;
  ordering: string;
  onQueryChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  onLabelChange: (value: string) => void;
  onOrderingChange: (value: string) => void;
  onSelect: (id: string) => void;
}

export function WorkspaceLibrary(props: WorkspaceLibraryProps) {
  return (
    <section className={styles.section}>
      <div className={styles.controls}>
        <input type="search" placeholder="Search documents" value={props.query} onChange={(event) => props.onQueryChange(event.target.value)} />
        <select value={props.statusFilter} onChange={(event) => props.onStatusChange(event.target.value)}>
          <option value="all">All statuses</option>
          <option value="done">Done</option>
          <option value="processing">Processing</option>
          <option value="error">Error</option>
        </select>
        <select value={props.labelFilter} onChange={(event) => props.onLabelChange(event.target.value)}>
          <option value="all">All types</option>
          <option value="invoice">Invoice</option>
          <option value="email">Email</option>
          <option value="resume">Resume</option>
          <option value="scientific_publication">Scientific Publication</option>
        </select>
        <select value={props.ordering} onChange={(event) => props.onOrderingChange(event.target.value)}>
          <option value="newest">Newest</option>
          <option value="oldest">Oldest</option>
          <option value="confidence">Confidence</option>
        </select>
      </div>

      <ul className={styles.list}>
        {props.documents.map((document) => (
          <li key={document.id} className={document.id === props.selectedId ? styles.activeItem : styles.item}>
            <button type="button" className={styles.rowButton} onClick={() => props.onSelect(document.id)}>
              <span>{document.filename}</span>
              <span>{document.label ?? 'Unclassified'}</span>
              <span>{document.confidence ? `${Math.round(document.confidence * 100)}%` : '--'}</span>
              <span>{formatFileSize(document.fileSize)}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

Create `frontend/src/components/workspace/WorkspaceDetailsPanel.tsx`:

```tsx
import type { DocumentResult } from '../../services/documents';
import styles from './WorkspaceDetailsPanel.module.css';

export function WorkspaceDetailsPanel({
  document,
  onOpenDetails,
}: {
  document: DocumentResult | null;
  onOpenDetails: () => void;
}) {
  if (!document) {
    return <aside className={styles.empty}>Select a document to inspect its results.</aside>;
  }

  return (
    <aside className={styles.panel}>
      <div className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Selected document</p>
          <h2>{document.filename}</h2>
        </div>
        <button type="button" onClick={onOpenDetails} aria-label={`View details for ${document.filename}`}>
          View details
        </button>
      </div>

      <dl className={styles.meta}>
        <div><dt>Status</dt><dd>{document.status}</dd></div>
        <div><dt>Uploaded</dt><dd>{document.createdAt ?? 'Unknown'}</dd></div>
        <div><dt>Predicted type</dt><dd>{document.classification?.predictedLabel ?? 'Pending'}</dd></div>
      </dl>

      {document.extraction ? (
        <div className={styles.invoiceBlock}>
          <p>Invoice Number: {document.extraction.invoiceNumber.value}</p>
          <p>Issuer: {document.extraction.issuerName.value}</p>
          <p>Total Amount: {document.extraction.totalAmount.value}</p>
        </div>
      ) : null}
    </aside>
  );
}
```

Replace the initial `frontend/src/pages/WorkspacePage.tsx` shell:

```tsx
import { Navbar } from '../components/layout/Navbar';
import { WorkspaceSummary } from '../components/workspace/WorkspaceSummary';
import { WorkspaceLibrary } from '../components/workspace/WorkspaceLibrary';
import { WorkspaceDetailsPanel } from '../components/workspace/WorkspaceDetailsPanel';
import { useAuth } from '../hooks/useAuth';
import { useWorkspace } from '../hooks/useWorkspace';
import styles from './WorkspacePage.module.css';

export function WorkspacePage() {
  const { user } = useAuth();
  const workspace = useWorkspace();

  return (
    <div className={styles.page}>
      <Navbar />
      <main className={styles.main}>
        {workspace.summary ? (
          <WorkspaceSummary summary={workspace.summary} displayName={user?.displayName ?? 'Workspace'} />
        ) : null}

        <div className={styles.grid}>
          <WorkspaceLibrary
            documents={workspace.documents}
            selectedId={workspace.selectedId}
            query={workspace.query}
            statusFilter={workspace.statusFilter}
            labelFilter={workspace.labelFilter}
            ordering={workspace.ordering}
            onQueryChange={workspace.setQuery}
            onStatusChange={workspace.setStatusFilter}
            onLabelChange={workspace.setLabelFilter}
            onOrderingChange={workspace.setOrdering}
            onSelect={workspace.setSelectedId}
          />
          <WorkspaceDetailsPanel
            document={workspace.selectedDocument}
            onOpenDetails={() => {
              if (workspace.selectedId) {
                workspace.setSelectedId(workspace.selectedId);
              }
            }}
          />
        </div>
      </main>
    </div>
  );
}
```

Update `frontend/src/components/layout/Navbar.tsx` so authenticated users can reach the workspace:

```tsx
import { Link } from 'react-router-dom';

<Link to="/workspace" className={styles.menuLink} onClick={() => setMenuOpen(false)}>
  Workspace
</Link>
```

Add matching styles in `frontend/src/components/layout/Navbar.module.css`:

```css
.menuLink {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  margin-top: 0.9rem;
  border-radius: 18px;
  border: 1px solid rgba(16, 24, 32, 0.08);
  background: rgba(255, 255, 255, 0.84);
  color: var(--color-text-primary);
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  text-decoration: none;
}
```

- [ ] **Step 4: Run the workspace UI test to verify it passes**

Run from `frontend/`:

```powershell
node .\node_modules\@playwright\test\cli.js test tests/workspace-library.spec.ts --config playwright.config.ts
```

Expected: PASS for the workspace stats/search/details flow.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/components/layout/Navbar.tsx frontend/src/components/layout/Navbar.module.css frontend/src/services/documents.ts frontend/src/types/index.ts frontend/src/services/workspace.ts frontend/src/hooks/useWorkspace.ts frontend/src/pages/WorkspacePage.tsx frontend/src/pages/WorkspacePage.module.css frontend/src/components/workspace/WorkspaceSummary.tsx frontend/src/components/workspace/WorkspaceSummary.module.css frontend/src/components/workspace/WorkspaceLibrary.tsx frontend/src/components/workspace/WorkspaceLibrary.module.css frontend/src/components/workspace/WorkspaceDetailsPanel.tsx frontend/src/components/workspace/WorkspaceDetailsPanel.module.css frontend/tests/workspace-library.spec.ts
git commit -m "feat: build workspace dashboard ui"
```

### Task 4: Wire document actions and normalize user-facing errors

**Files:**
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/services/documents.ts`
- Modify: `frontend/src/hooks/useAnalysis.ts`
- Modify: `frontend/src/components/layout/AuthDialog.tsx`
- Modify: `frontend/src/pages/WorkspacePage.tsx`
- Create: `frontend/src/services/errorMessages.ts`
- Test: `frontend/tests/workspace-actions.spec.ts`

- [ ] **Step 1: Write the failing action/error test**

Create `frontend/tests/workspace-actions.spec.ts`:

```ts
import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('auth_access', 'workspace-access');
    localStorage.setItem('auth_refresh', 'workspace-refresh');
  });

  await page.route('**/api/profile/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          id: 3,
          username: 'vako',
          email: 'vako@example.com',
          profile: {
            display_name: 'Vako',
            avatar_url: '',
            created_at: '2026-04-14T11:00:00Z',
          },
        },
      }),
    });
  });

  await page.route('**/api/workspace/summary/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          totals: {
            uploads: 1,
            processed: 1,
            errors: 0,
            invoices: 1,
          },
          dominant_label: { value: 'invoice', count: 1 },
          recent_invoice_total: '205.50',
          recent_activity: [],
        },
      }),
    });
  });

  await page.route('**/api/documents/?**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 'c0f4e5c4-2a2f-4544-9cd7-3a69a4158f11',
              filename: 'invoice-b.pdf',
              content_type: 'application/pdf',
              file_size: 1200,
              status: 'done',
              label: 'invoice',
              confidence: 0.97,
              created_at: '2026-04-14T12:00:00Z',
              updated_at: '2026-04-14T12:05:00Z',
            },
          ],
        },
      }),
    });
  });

  await page.route('**/api/documents/c0f4e5c4-2a2f-4544-9cd7-3a69a4158f11/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          id: 'c0f4e5c4-2a2f-4544-9cd7-3a69a4158f11',
          filename: 'invoice-b.pdf',
          content_type: 'application/pdf',
          file_size: 1200,
          status: 'done',
          created_at: '2026-04-14T12:00:00Z',
          updated_at: '2026-04-14T12:05:00Z',
          classification: {
            predicted_label: 'invoice',
            confidence: 0.97,
            all_scores: { invoice: 0.97 },
            model_version: 'test-model',
            classified_at: '2026-04-14T12:05:00Z',
          },
          invoice_data: null,
        },
      }),
    });
  });
});

test('workspace actions surface specific backend errors', async ({ page }) => {
  await page.route('**/api/documents/c0f4e5c4-2a2f-4544-9cd7-3a69a4158f11/classify/', async (route) => {
    await route.fulfill({
      status: 422,
      contentType: 'application/json',
      body: JSON.stringify({
        error: {
          code: 'UNPROCESSABLE',
          message: 'Document is already being processed.',
          field_errors: {},
        },
      }),
    });
  });

  await page.route('**/api/documents/c0f4e5c4-2a2f-4544-9cd7-3a69a4158f11/download/', async (route) => {
    await route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({
        error: {
          code: 'NOT_FOUND',
          message: 'Document not found.',
          field_errors: {},
        },
      }),
    });
  });

  await page.goto('/workspace');

  await page.getByRole('button', { name: /re-run analysis/i }).click();
  await expect(page.getByRole('alert')).toContainText('This document is already being processed.');

  await page.getByRole('button', { name: /download/i }).click();
  await expect(page.getByRole('alert')).toContainText('We could not download that document.');
});

test('home upload surfaces a specific unsupported-type error', async ({ page }) => {
  await page.route('**/api/documents/', async (route) => {
    await route.fulfill({
      status: 415,
      contentType: 'application/json',
      body: JSON.stringify({
        error: {
          code: 'UNSUPPORTED_MEDIA_TYPE',
          message: \"File type 'image/gif' is not supported.\",
          field_errors: {},
        },
      }),
    });
  });

  await page.goto('/');

  const uploadArea = page.getByRole('button', {
    name: /upload documents by drag and drop, click to browse, or paste when focused/i,
  });

  await uploadArea.evaluate((element) => {
    const input = element.querySelector('input[type=\"file\"]') as HTMLInputElement;
    const file = new File(['gif'], 'unsupported.gif', { type: 'image/gif' });
    const data = new DataTransfer();
    data.items.add(file);
    input.files = data.files;
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });

  await page.getByRole('button', { name: /analyze all/i }).click();
  await expect(page.getByText(/supported document types are pdf, png, jpg, jpeg, and tiff/i)).toBeVisible();
});
```

- [ ] **Step 2: Run the action/error test to verify it fails**

Run from `frontend/`:

```powershell
node .\node_modules\@playwright\test\cli.js test tests/workspace-actions.spec.ts --config playwright.config.ts
```

Expected: FAIL because the workspace has no action buttons yet and the home flow still uses generic error copy.

- [ ] **Step 3: Implement action helpers and shared error normalization**

Create `frontend/src/services/errorMessages.ts`:

```ts
import { ApiRequestError } from './api';

type ErrorContext = 'auth' | 'upload' | 'analysis' | 'workspace';

export function getUserFacingError(error: unknown, context: ErrorContext, fallback: string): string {
  if (error instanceof ApiRequestError) {
    if (context === 'upload' && error.code === 'UNSUPPORTED_MEDIA_TYPE') {
      return 'Supported document types are PDF, PNG, JPG, JPEG, and TIFF.';
    }
    if (context === 'upload' && error.code === 'FILE_TOO_LARGE') {
      return error.message;
    }
    if (context === 'workspace' && error.code === 'NOT_FOUND') {
      return 'We could not download that document.';
    }
    if (context === 'workspace' && error.code === 'UNPROCESSABLE') {
      return 'This document is already being processed.';
    }
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
}
```

Extend `frontend/src/services/documents.ts` with workspace actions:

```ts
export async function downloadDocument(id: string): Promise<string> {
  const data = await api.get<{ url: string }>(`/documents/${id}/download/`);
  return data.url;
}

export async function rerunDocumentAnalysis(id: string): Promise<void> {
  await api.post(`/documents/${id}/classify/`);
}
```

Update `frontend/src/hooks/useAnalysis.ts` so upload and polling errors use the shared helper:

```ts
import { getUserFacingError } from '../services/errorMessages';

error: getUserFacingError(err, 'upload', 'Upload failed.')
error: getUserFacingError(err, 'analysis', 'Analysis failed on the server.')
```

Update `frontend/src/components/layout/AuthDialog.tsx` so general errors come from the same mapper when there are no field errors:

```ts
import { getUserFacingError } from '../../services/errorMessages';

setGeneralError(getUserFacingError(err, 'auth', fallbackMessage));
```

Replace `frontend/src/pages/WorkspacePage.tsx` action handling with explicit feedback:

```tsx
import { deleteDocument, downloadDocument, rerunDocumentAnalysis } from '../services/documents';
import { getUserFacingError } from '../services/errorMessages';

const [actionError, setActionError] = useState<string | null>(null);

const handleDownload = async () => {
  if (!workspace.selectedId) return;
  try {
    const url = await downloadDocument(workspace.selectedId);
    window.open(url, '_blank', 'noopener,noreferrer');
    setActionError(null);
  } catch (error) {
    setActionError(getUserFacingError(error, 'workspace', 'We could not download that document.'));
  }
};

const handleRerun = async () => {
  if (!workspace.selectedId) return;
  try {
    await rerunDocumentAnalysis(workspace.selectedId);
    setActionError(null);
  } catch (error) {
    setActionError(getUserFacingError(error, 'workspace', 'We could not re-run analysis.'));
  }
};

const handleDelete = async () => {
  if (!workspace.selectedId) return;
  try {
    await deleteDocument(workspace.selectedId);
    setActionError(null);
    workspace.reload();
  } catch (error) {
    setActionError(getUserFacingError(error, 'workspace', 'We could not delete that document.'));
  }
};
```

Render the feedback banner and action buttons inside the workspace page:

```tsx
{actionError ? <div role="alert">{actionError}</div> : null}

<div className={styles.actions}>
  <button type="button" onClick={handleDownload}>Download</button>
  <button type="button" onClick={handleRerun}>Re-run analysis</button>
  <button type="button" onClick={handleDelete}>Delete</button>
</div>
```

- [ ] **Step 4: Run the action/error test to verify it passes**

Run from `frontend/`:

```powershell
node .\node_modules\@playwright\test\cli.js test tests/workspace-actions.spec.ts --config playwright.config.ts
```

Expected: PASS for both the workspace action errors and the upload unsupported-type error.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/services/api.ts frontend/src/services/documents.ts frontend/src/hooks/useAnalysis.ts frontend/src/components/layout/AuthDialog.tsx frontend/src/pages/WorkspacePage.tsx frontend/src/services/errorMessages.ts frontend/tests/workspace-actions.spec.ts
git commit -m "feat: normalize app errors and workspace actions"
```

### Task 5: Run regression verification and publish the feature branch

**Files:**
- Modify: none
- Test: `backend/apps/documents/tests/test_workspace_api.py`
- Test: `frontend/tests/workspace-route.spec.ts`
- Test: `frontend/tests/workspace-library.spec.ts`
- Test: `frontend/tests/workspace-actions.spec.ts`
- Test: `frontend/tests/auth-dialog-feedback.spec.ts`
- Test: `frontend/tests/auth-dialog-position.spec.ts`
- Test: `frontend/tests/auth-dialog-error-scroll.spec.ts`
- Test: `frontend/tests/upload-paste.spec.ts`

- [ ] **Step 1: Run backend verification**

Run from the repo root:

```powershell
docker compose exec api python -m pytest apps/documents/tests/test_workspace_api.py -v
```

Expected: PASS.

- [ ] **Step 2: Run targeted frontend regression tests**

Run from `frontend/`:

```powershell
node .\node_modules\@playwright\test\cli.js test tests/workspace-route.spec.ts tests/workspace-library.spec.ts tests/workspace-actions.spec.ts tests/auth-dialog-feedback.spec.ts tests/auth-dialog-position.spec.ts tests/auth-dialog-error-scroll.spec.ts tests/upload-paste.spec.ts --config playwright.config.ts
```

Expected: PASS for the new workspace flows and the recent auth/upload regressions.

- [ ] **Step 3: Run build and lint verification**

Run from `frontend/`:

```powershell
npm.cmd run build
npm.cmd run lint
```

Expected:
- build PASS
- lint PASS

- [ ] **Step 4: Push the branch to GitHub**

Run from the repo root:

```powershell
git push -u origin feature/workspace-dashboard-history
```

Expected: branch published successfully on GitHub.

- [ ] **Step 5: Final check**

Confirm the branch contains:

```powershell
git status --short
git log --oneline -5
```

Expected:
- clean or intentionally staged working tree
- recent commits for routing, backend summary, workspace UI, and error handling
