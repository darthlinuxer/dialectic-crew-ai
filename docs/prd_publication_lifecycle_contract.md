# PRD Publication Lifecycle Contract

## Purpose

This document is the single authoritative, implementation-facing contract for PRD output handling and publication lifecycle decisions.

It defines the required terminology, the lifecycle contexts, and the decision rules that separate:

- the **client-visible emitted view**, from
- the **compliance-grade persistence requirements**.

All PRD publication code, APIs, tests, and future workflow integrations must conform to this contract.

## Authoritative Terms

### `canonical_model`

The `canonical_model` is the internal PRD representation and the sole source of truth for PRD content.

Normative requirements:

- The `canonical_model` MUST remain the authoritative internal representation.
- No emitted, rendered, persisted, previewed, exported, or published artifact may supersede the `canonical_model`.
- Any Markdown or JSON artifact MUST be derived from the `canonical_model`, not edited into authority after generation.

### `render`

`render` is the transformation step that derives one or more client- or artifact-facing views from the `canonical_model`.

Normative requirements:

- `render` MUST produce Markdown and/or JSON views from the `canonical_model`.
- `render` MUST NOT redefine source-of-truth status.
- `render` MAY be invoked in preview, export, or publication flows.
- `render` output is a view of the `canonical_model`, not a replacement for it.

### `emit`

`emit` controls what is returned, streamed, or displayed to the client in a given operation.

Normative requirements:

- `emit` determines the client-visible output only.
- `emit` MAY return Markdown, JSON, or both, depending on the request and lifecycle context.
- `emit` MUST NOT be used as the rule that determines compliance-grade persistence obligations.
- A request for a specific emitted view does not alter publication persistence requirements.

### `persist`

`persist` controls what artifacts are written to durable storage as governed outputs.

Normative requirements:

- `persist` determines what is written as approval-grade artifacts.
- `persist` rules are governed by lifecycle context, not merely by requested emitted format.
- `persist` MUST satisfy publication and compliance obligations even when `emit` returns only one format to the client.

### `preview`

`preview` is a non-approval, pre-publication interaction that allows inspection of rendered PRD views without creating approval-grade published artifacts.

Normative requirements:

- `preview` operates before approval.
- `preview` MAY `render` and `emit` Markdown, JSON, or both.
- `preview` MUST NOT be treated as `publish`.
- `preview` MUST NOT create approved-publication artifacts in `prd_output/` as a substitute for governed publication.

### `export`

`export` is a non-governed output operation that produces a requested rendered format for convenience, transfer, or inspection outside the approval-grade publication path.

Normative requirements:

- `export` MAY `render`, `emit`, and optionally `persist` requested views according to product behavior.
- `export` is not itself governed publication.
- `export` MUST NOT imply approval or satisfy the requirements of `publish` unless it explicitly executes the approved publication contract.

### `publish`

`publish` is the governed operation that creates approval-grade PRD artifacts.

Normative requirements:

- `publish` MAY occur only after full dialectic validation has completed successfully.
- `publish` MUST operate only in the `approved_publication` lifecycle context.
- `publish` MUST `persist` both Markdown and JSON artifacts in `prd_output/`.
- `publish` requirements apply regardless of which single view, if any, is `emit`ted to the client.
- `publish` is the only operation that creates the governed approved-publication artifact set.

### `approved_publication`

`approved_publication` is both:
1. a lifecycle context, and
2. the resulting governed state of a PRD after all required approval and validation conditions are satisfied.

Normative requirements:

- `approved_publication` exists only after full dialectic validation and approval gating are satisfied.
- In `approved_publication`, persistence requirements are stricter than client emission requirements.
- `approved_publication` MUST result in both `.md` and `.json` artifacts being persisted in `prd_output/`.

## Lifecycle Contexts

The PRD output lifecycle has exactly three explicit contexts for output-handling decisions.

### `pre_approval_preview`

`pre_approval_preview` is the context used before approval has been granted.

Characteristics:

- The `canonical_model` remains the sole source of truth.
- The system MAY `render` Markdown and/or JSON from the `canonical_model`.
- The system MAY `emit` one or both views to the client.
- The system MUST treat outputs as preview material, not approved publication artifacts.
- The system MUST NOT treat a preview response as satisfying publication persistence obligations.

Decision rule:

- In `pre_approval_preview`, `emit` is client-facing convenience only; `persist` does not create approval-grade published artifacts.

### `approved_publication`

`approved_publication` is the governed context entered only after full dialectic validation and all required approval conditions have passed.

Characteristics:

- The `canonical_model` remains the sole source of truth.
- The system MAY `render` Markdown and JSON views from the `canonical_model`.
- The system MAY `emit` whichever view the client requested.
- The system MUST `persist` both `.md` and `.json` as approval-grade artifacts in `prd_output/`.
- The persistence requirement is mandatory even if the client only requested Markdown or only requested JSON.

Decision rule:

- In `approved_publication`, `emit` controls client-visible response shape, but `persist` is governed by compliance and publication rules and therefore MUST write both formats to `prd_output/`.

### `ad_hoc_export`

`ad_hoc_export` is the context for non-governed, convenience-oriented output generation outside the approved publication path.

Characteristics:

- The `canonical_model` remains the sole source of truth.
- The system MAY `render` Markdown and/or JSON from the `canonical_model`.
- The system MAY `emit` or optionally `persist` exported views according to feature needs.
- The system MUST NOT imply that ad hoc outputs are approved-publication artifacts unless the governed `publish` operation is executed.

Decision rule:

- In `ad_hoc_export`, requested format may drive what is emitted or exported, but that does not satisfy the governed persistence contract reserved for `approved_publication`.

## Decision Contract: Emit vs Persist

This section is the implementation-facing rule set that separates client-visible behavior from compliance-grade artifact storage.

### Rule 1: Source of truth

- The `canonical_model` is always the sole source of truth.
- All Markdown and JSON outputs are rendered views derived from the `canonical_model`.

### Rule 2: Rendering is not authority

- `render` creates Markdown and/or JSON views.
- Rendered views do not become authoritative merely because they are emitted or persisted.

### Rule 3: Emit is client-facing only

- `emit` decides what the caller sees or receives.
- `emit` may vary by request.
- `emit` MUST NOT weaken or redefine persistence obligations.

### Rule 4: Persist is governance-facing

- `persist` decides what durable artifacts are written.
- `persist` is determined by lifecycle context and governance requirements, not only by request shape.

### Rule 5: Preview and export do not equal publication

- `preview` and `export` may produce useful rendered outputs.
- Neither `preview` nor `export` constitutes governed `publish` unless the approved publication contract is explicitly executed.

### Rule 6: Approved publication requires dual persistence

- `publish` can only occur after full dialectic validation.
- When `publish` occurs in `approved_publication`, the system MUST persist both Markdown and JSON artifacts in `prd_output/`.
- This requirement applies regardless of whether the client-facing emitted view is Markdown-only, JSON-only, both, or none.

## Required Publication Behavior

For any governed PRD publication flow, the system MUST enforce all of the following:

1. Load the PRD `canonical_model` as the only source of truth.
2. `render` Markdown and JSON views from that `canonical_model`.
3. Ensure full dialectic validation has completed successfully before `publish`.
4. Enter the `approved_publication` lifecycle context before publication artifacts are finalized.
5. `persist` both:
   - `prd_output/<name>.md`
   - `prd_output/<name>.json`
6. Allow `emit` to return the requested client-facing view independently of the persistence requirement.
7. Treat the persisted dual-format artifact set as the compliance-grade approved publication record.

## Implementation Guidance

Implementers should use the following decision table.

| Context | Render allowed | Emit allowed | Persist allowed | Publish allowed | Required persisted artifacts |
| --- | --- | --- | --- | --- | --- |
| `pre_approval_preview` | Yes | Yes | Limited/non-publication only | No | Not approval-grade publication artifacts |
| `approved_publication` | Yes | Yes | Yes | Yes, after full dialectic validation | Both `.md` and `.json` in `prd_output/` |
| `ad_hoc_export` | Yes | Yes | Optional, non-governed export behavior | No, unless separately routed through governed publish flow | Context-specific export outputs only |

## Macro-Vision Alignment

This contract is intentionally anti-drift aligned with `internal/SELF_VISION.md`.

Normative alignment statements:

- This contract implements the publication-lifecycle distinction required by the system vision.
- The `canonical_model` remains authoritative at all times.
- Rendering is derivative, not authoritative.
- Client-visible `emit` behavior is separate from governance-grade `persist` behavior.
- Governed `publish` is gated and may occur only after full dialectic validation.
- Approved publication requires dual-format persistence in `prd_output/` to maintain a durable, compliance-grade artifact set.

## Non-Negotiable Compliance Statement

A PRD is not considered successfully published unless all of the following are true:

- it is in the `approved_publication` context,
- full dialectic validation has completed successfully,
- the publication operation has persisted both `.md` and `.json`,
- those artifacts are written to `prd_output/`,
- and any client-facing emitted view is treated as separate from the compliance-grade persistence obligation.

This document is the definitive contract for those rules.
