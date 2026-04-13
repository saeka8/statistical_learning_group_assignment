# Refined Pulse Frontend Design

Date: 2026-04-13
Project: `frontend`
Status: Approved design, pending implementation plan

## Summary

This design updates three parts of the DocLens frontend:

1. The hero visual on the right will keep the current extraction-inspired composition but gain subtle, classy motion.
2. The dark workspace dock in the demo area will be replaced by a light glass workflow summary that matches the rest of the site.
3. Multi-document analysis results will become explicitly switchable and easier to understand by showing document names and active selection across the result views.

The visual tone should stay calm, polished, and presentation-friendly. Motion should add life without creating lag, noise, or a "tech demo" feel.

## Goals

- Make the hero feel alive and memorable while preserving the current elegant aesthetic.
- Remove the visual disconnect caused by the dark demo dock.
- Make it obvious which analyzed document is currently being inspected.
- Allow fast switching between analyzed documents without re-running analysis.
- Surface document identity consistently in the classification and extraction areas.

## Non-Goals

- No heavy WebGL or particle-heavy motion for the hero.
- No large information-architecture changes to the page.
- No backend or ML logic changes.
- No introduction of complex timeline controls or carousel behavior.

## Design Direction

The chosen direction is `Refined Pulse`.

This direction keeps the existing soft editorial/glass feel and adds motion in a restrained way:

- The hero uses quiet scanning and emphasis cues rather than dramatic 3D movement.
- The workspace summary becomes a light, integrated status surface instead of a dark operator console.
- The result experience emphasizes clarity and document identity before adding any visual flourish.

## Hero Visual

### Intent

The current right-side hero mockup already fits the site, so it should be evolved rather than replaced. The visual should feel like a live extraction surface that is gently "reading" the page.

### Visual Changes

- Preserve the current document/extraction card structure in `Scene3D`.
- Add a slow horizontal scan highlight that passes over the paper/extraction area.
- Add small field emphasis states that softly glow or fade in sequence.
- Add one or two quiet confidence/status accents that reinforce the idea of analysis in progress.
- Keep gradients, borders, and color palette aligned with existing blue/ink/sand tokens.

### Motion Rules

- Motion should be CSS-driven where possible.
- Use long durations and low amplitude.
- No jitter, bounce, or frequent looping elements.
- Respect `prefers-reduced-motion` by disabling looping or replacing it with static emphasis.

### Performance Constraints

- Avoid expensive blur-heavy animations that repaint large areas continuously.
- Avoid canvas or heavy 3D animation for this surface.
- Limit the number of simultaneously animated elements.

## Workspace Summary Replacement

### Problem

The current dark dock in `UploadWorkspace` feels disconnected from the surrounding light glass system and does not clearly justify why it exists.

### Replacement

Replace the dark dock with a light glass `workflow summary` card that belongs visually to the same family as the queue and upload panels.

### Contents

- Current phase label and short status sentence.
- Staged document count.
- Short workflow signals or pipeline hints, but in a lighter and more legible presentation.
- Optional subtle active-state pulse or accent line when processing is underway.

### Styling

- Use pale glass backgrounds and soft borders.
- Reuse the existing ink, blue, and sand accents.
- Keep depth from shadows and layered gradients, not from a hard dark block.

## Multi-Document Results Experience

### Problem

The app already tracks an active document, but the results area does not make that selection obvious enough. When several files are analyzed, users can miss that only one document's breakdown is being shown.

### Required Behavior

- Users must be able to switch between analyzed documents after analysis completes.
- The selected document name must be visible in the results area.
- Classification and extraction panels must update instantly when the active document changes.
- Invoice extraction should only render for documents classified as invoices and with extraction data present.

### Result Navigation Pattern

Add a compact document switcher above the classification section and reuse the same selection context for the extraction section.

Recommended structure:

- A small label such as `Analyzed documents`.
- A row or wrapped list of document chips/tabs using the real file names.
- Clear active styling tied to the same active-document state used in the workspace queue.

### Result Header Changes

Classification section:

- Show the active document name near the heading.
- Keep the prediction card prominent.
- Make the section read as "results for this document," not "global batch result."

Extraction section:

- Show the active document name there as well.
- If the selected document has no extraction, do not show the extraction section.

### Selection Source of Truth

`activeDocumentId` in `useAnalysis` remains the single source of truth.

The implementation should ensure:

- Clicking a document in the queue updates `activeDocumentId`.
- Clicking a document chip in the results area also updates `activeDocumentId`.
- When documents are added, the newest added item may become active.
- When analysis completes, the currently selected document stays selected unless no active document exists.

## Component-Level Plan

### `frontend/src/components/3d/Scene3D.tsx`

- Extend the hero mockup markup with a few semantic elements for the scan line and signal accents.
- Keep the overall structure recognizable to avoid a full redesign.

### `frontend/src/components/3d/Scene3D.module.css`

- Add restrained looping animation rules for the scan line and field emphasis.
- Add reduced-motion fallbacks.
- Keep the motion lightweight and primarily transform/opacity based.

### `frontend/src/components/sections/UploadWorkspace.tsx`

- Replace the dark dock content structure with a light workflow summary card.
- Keep the same conceptual information where useful, but present it as integrated status rather than a separate console.

### `frontend/src/components/sections/UploadWorkspace.module.css`

- Introduce new summary-card styling aligned with the page palette.
- Remove the visual language that makes the current dark block feel unrelated.

### `frontend/src/components/sections/ClassificationResults.tsx`

- Add document identity and a switcher for analyzed documents.
- Accept the minimum extra props needed to render document names and switch active selection.

### `frontend/src/components/sections/ClassificationResults.module.css`

- Style the switcher chips/tabs and active states.
- Add small metadata styling for active document context.

### `frontend/src/components/sections/InvoiceExtraction.tsx`

- Surface the active document name in the extraction header.

### `frontend/src/components/sections/InvoiceExtraction.module.css`

- Add styles for the document context line if needed.

### `frontend/src/App.tsx`

- Pass document list, active document metadata, and selection callback into results components.
- Keep the current visibility rules for classification/extraction, but make them active-document aware.

## Accessibility

- Result switcher items must be keyboard accessible.
- Active state must be visually clear and not rely on color alone.
- Motion must respect `prefers-reduced-motion`.
- File names should remain legible and truncate gracefully where needed.

## Testing and Verification

- Verify hero renders correctly on desktop and mobile.
- Verify reduced-motion mode removes or minimizes looping hero effects.
- Verify queue selection and result-chip selection both change the visible result.
- Verify switching from an invoice document to a non-invoice document hides extraction cleanly.
- Verify multiple analyzed documents remain individually inspectable after batch analysis.
- Run frontend build and lint after implementation.

## Risks and Mitigations

- Risk: hero motion becomes too busy.
  Mitigation: restrict animation to one scan line and a few soft opacity/transforms only.

- Risk: result switching duplicates state or falls out of sync with queue selection.
  Mitigation: keep `activeDocumentId` as the only selection source.

- Risk: lighter workspace summary loses useful emphasis.
  Mitigation: retain hierarchy with spacing, subtle accents, and stronger type rather than dark contrast.
