# Workspace Dashboard And Document History Design

## Summary

Build a protected `workspace` experience for authenticated users so DocLens feels like a real document product, not only a one-off demo. The public landing page remains the acquisition and live-demo surface at `/`, while a new private `/workspace` route becomes the long-lived account area for document history, practical statistics, and document management actions.

The new workspace should feel editorial, trustworthy, and client-facing. It should expose a user's upload history, high-value usage stats, recent activity, and a focused details view for classification and invoice extraction results. The backend should support this with a small, intentional expansion instead of a parallel subsystem.

## Goals

- Add a dedicated protected `/workspace` page for logged-in users.
- Make document history persistent and easy to browse.
- Surface practical usage statistics that feel useful to a client.
- Let users manage stored documents with clear actions:
  - view details
  - download
  - re-run analysis
  - delete
- Improve user-facing error messaging across auth, uploads, analysis, and workspace actions.
- Keep the existing public homepage and live upload flow intact.

## Non-Goals

- Replacing the public homepage with the workspace.
- Building a multi-page back-office/admin product.
- Adding collaborative sharing, folders, tags, or team accounts.
- Reworking the ML pipeline itself.
- Adding a separate upload workflow inside the workspace in this phase.

## Product Direction

DocLens should behave like a product with two clear surfaces:

- `/`
  Public landing page and live demo workspace.
- `/workspace`
  Private user account area for history, metrics, and management.

This split keeps the homepage persuasive and visually striking, while the workspace becomes calmer, more practical, and more trustworthy.

## User Experience

### Navigation

- Keep the current navbar on the landing page.
- Promote auth state to app level so the full app can react to login/logout.
- Add a `Workspace` action to the authenticated account menu.
- Keep `Sign out` in the same menu.
- If a logged-out user navigates to `/workspace`, redirect them back to `/` and open the auth flow or show a clear login prompt state.

### Workspace Page Layout

The workspace should feel like a private editorial control room with restrained motion and premium surfaces.

#### 1. Workspace Header

Show:

- page title and short account summary
- personalized greeting using the profile display name
- supporting description that reinforces persistent history and analysis continuity

#### 2. Practical Stat Cards

Show 3-4 top-level cards built from backend data:

- total uploads
- processed successfully
- invoices detected
- most common document type

Use `recent invoice total` only when at least one extracted invoice in the summary window has a numeric `total_amount`. Otherwise keep the four primary cards above and do not render a currency card.

#### 3. Recent Activity Band

A compact strip or cluster showing recent uploads and latest completed processing. This is meant to answer “what happened lately?” at a glance.

#### 4. Document Library

The main area contains:

- search by filename
- filters for status and document type
- sort options:
  - newest
  - oldest
  - confidence

Each library item should display:

- filename
- upload timestamp
- status
- predicted document type
- confidence
- size

#### 5. Document Actions

Each item should expose:

- `View details`
- `Download`
- `Re-run analysis`
- `Delete`

Actions must produce specific success/failure feedback rather than generic errors.

#### 6. Details Panel

Selecting a document opens a details area on the same page rather than navigating away.

The details panel should show:

- file metadata
- classification label and confidence
- score breakdown when available
- invoice extraction fields when the document is an invoice
- last processed state and timestamps where available

This panel keeps the page feeling like a real workspace rather than a list that sends people away for every action.

## Frontend Architecture

### Routing

The app should move from a single-route shell to a small routed structure.

Recommended route map:

- `/` -> landing page
- `/workspace` -> protected workspace page

Use a lightweight router and preserve the current landing page composition.

### Shared Auth State

Current auth state lives inside the navbar hook, which is too local for protected routes. Introduce a shared auth provider/context so the app can:

- know whether a user is authenticated
- access the current profile anywhere
- trigger login/register/logout without prop drilling
- gate `/workspace` properly

### Page Composition

Refactor the current landing page into a dedicated page component rather than keeping everything inside `App.tsx`.

Proposed structure:

- app shell / providers
- public landing page
- protected workspace page
- shared auth dialog
- shared navbar/account menu

This keeps page-level concerns readable and prevents the workspace from becoming another giant section in the homepage file.

## Backend Design

### Existing Endpoints To Keep

Retain current document endpoints for:

- list/create
- detail/delete
- download
- classify
- classification status
- extraction

### Workspace Summary Endpoint

Add a dedicated endpoint such as:

- `GET /api/workspace/summary/`

This endpoint should return practical, server-computed account data for the authenticated user:

- total upload count
- processed success count
- error count
- invoice count
- most common predicted type
- recent invoice total when computable
- recent activity items

This avoids fragile frontend-only aggregation for top-level account stats.

### Document List Expansion

Extend the existing documents list endpoint so the workspace can use it directly.

Add support for:

- filename search
- filter by status
- filter by predicted label
- sort by:
  - newest
  - oldest
  - confidence descending

If pagination already exists, preserve it and make the workspace page pagination-aware.

### Document Detail Contract

Keep the existing detail endpoint as the source of truth for the details panel, but ensure it exposes the fields needed by the new UI without frontend guesswork.

The detail response should remain rich enough to render:

- metadata
- classification
- invoice extraction
- relevant timestamps

## Error Handling Strategy

The app should stop flattening unlike failures into the same generic messages.

### Auth

- Field-level validation should stay inline.
- General auth failures stay in the banner area.
- Wrong password / invalid credentials must not look like field validation.

### Upload

Support specific feedback for:

- unsupported file type
- file too large
- missing file
- network/upload failure

### Analysis

Differentiate:

- server-side processing failure
- request/network failure
- already processing / re-run blocked states

### Workspace Actions

Give action-specific errors for:

- failed download
- failed delete
- failed detail fetch
- failed re-run
- document not found

### Frontend Error Normalization

Introduce a small shared frontend mapping layer so components can convert backend/API errors into intentional user-facing messages instead of repeating fallback strings in each feature.

## Visual Direction

The workspace should not reuse the landing page’s more theatrical presentation rhythm one-to-one. It should feel:

- calmer
- lighter
- more editorial
- more product-like

Design language:

- soft glass panels
- clean information hierarchy
- restrained motion
- elegant typography
- strong spacing and compositional clarity

The memorable quality should come from refinement and confidence rather than visual noise.

## Testing Strategy

### Frontend

Add tests for:

- protected route behavior for `/workspace`
- authenticated navigation from account menu to workspace
- workspace stats rendering from backend responses
- search/filter/sort behavior
- document details panel rendering
- download / delete / re-run flows
- specific error states for document actions

### Backend

Add tests for:

- workspace summary endpoint
- document search/filter/sort behavior
- authorization boundaries so users only see their own documents
- summary aggregation correctness

### Regression Coverage

Do not regress recent auth/upload improvements:

- scrolled auth dialog behavior
- inline auth errors
- paste-to-upload while focused

## Edge Cases

- Users with zero documents should see a high-quality empty state rather than blank stats.
- Documents without classification yet should still appear clearly with status context.
- Documents with classification but no extraction should render gracefully.
- Failed documents should remain visible in history with actionable messaging.
- Very long filenames should truncate cleanly without hiding actions.
- Empty invoice totals should not render as misleading currency values.
- Workspace must remain usable on smaller laptop screens and mobile widths.

## Branch And Delivery Workflow

- Create and work on a dedicated branch:
  - `feature/workspace-dashboard-history`
- Keep the work isolated from `main`
- Push the branch to GitHub once implementation is verified

## Implementation Outline

The implementation should likely proceed in this order:

1. Introduce routing and shared auth state.
2. Add protected workspace navigation.
3. Implement backend summary endpoint and document query extensions.
4. Build workspace page layout and data hooks.
5. Add document actions and details panel behavior.
6. Unify user-facing error handling.
7. Add automated tests and verify core flows.

## Success Criteria

This work is successful when:

- a logged-in user can open `/workspace`
- they can browse their upload history and account stats
- they can view details, download, delete, and re-run document analysis
- the page feels like a polished product area, not a classroom afterthought
- errors are specific and understandable across the main user flows
- the work lives on a dedicated Git branch ready to push to GitHub
