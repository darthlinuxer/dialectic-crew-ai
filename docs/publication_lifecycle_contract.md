# Publication Lifecycle Contract

This document is the authoritative implementation-facing contract for PRD output handling.

## Status

Normative. All PRD generation, preview, export, approval, and publication flows MUST conform to this contract.

## Purpose

This contract defines the lifecycle terminology and decision rules that govern how PRD outputs are derived, returned, displayed, exported, and persisted. It exists to prevent drift between:

- the internal PRD representation,
- client-visible views,
- ad hoc exports, and
- compliance-grade approved publication artifacts.

This contract is aligned with `internal/SELF_VISION.md` and its requirement that approved PRDs be persisted in both Markdown and JSON formats in `prd_output/`.

## Normative terminology

### `canonical_model`

The `canonical_model` is the sole source of truth for a PRD within the system.

Requirements:

- The `canonical_model` MUST contain the authoritative internal representation of the PRD.
- All downstream representations MUST be derived from the `canonical_model`.
- No emitted, rendered, exported, previewed, or persisted artifact may become a replacement source of truth for the PRD.
- Mutations to PRD content MUST occur against the `canonical_model`, not against rendered outputs.

Implementation meaning:

- Internal logic should treat the `canonical_model` as the only authoritative state.
- Markdown and JSON files are outputs derived from the `canonical_model`, not independent authorities.
- In other words, rendering produces Markdown and/or JSON views from the `canonical_model`.

### `render`

`render` is the deterministic transformation of the `canonical_model` into one or more external representations.

Requirements:

- `render` MUST derive output views from the `canonical_model`.
- `render` MAY produce Markdown, JSON, or both.
- `render` MUST NOT redefine, mutate, or supersede the `canonical_model`.
- Rendered views are representations of the `canonical_model`, not new state authorities.

Implementation meaning:

- Rendering produces Markdown and/or JSON views from the `canonical_model`.
- A renderer may be used for preview, export, emit, or persist flows, but those lifecycle decisions are separate from rendering itself.

### `emit`

`emit` controls what is returned, streamed, or displayed to the client.

Requirements:

- `emit` MUST define client-visible output behavior.
- `emit` MAY return Markdown, JSON, both, or neither, depending on the lifecycle context.
- `emit` MUST remain distinct from `persist`.
- A client-visible response MUST NOT be interpreted as proof of approval-grade persistence.

Implementation meaning:

- `emit` answers: “What does the user or caller receive now?”
- `emit` does not answer: “What artifacts are written as governed records?”

### `persist`

`persist` controls what artifacts are written to storage as system records.

Requirements:

- `persist` MUST define storage behavior independently from `emit`.
- `persist` MAY be disallowed, optional, contextual, or mandatory depending on lifecycle context.
- Approval-grade persistence requirements MUST be stricter than preview or ad hoc export behavior.
- Compliance-grade persistence MUST never depend solely on what was emitted to the client.

Implementation meaning:

- `persist` answers: “What durable artifacts are written by the system?”
- For governed publication, `persist` is mandatory and subject to stricter requirements than preview or export.

### `preview`

`preview` is a client-facing inspection experience before approval.

Requirements:

- `preview` MUST be treated as pre-approval and non-governing.
- `preview` MAY use `render` and `emit`.
- `preview` MUST NOT be treated as `publish`.
- `preview` MUST NOT create approval-grade records unless explicitly stated by another contract.

Implementation meaning:

- Preview is for review and iteration before approval.
- A preview may display Markdown, JSON, or both, without creating the final governed publication artifacts.

### `export`

`export` is the creation or delivery of a user-requested representation outside the governed approval publication path.

Requirements:

- `export` MAY produce Markdown, JSON, or both from the `canonical_model`.
- `export` MAY be emitted to a client and MAY be persisted as a convenience artifact.
- `export` MUST NOT be treated as approved publication unless it satisfies the governed `publish` contract.
- Exported artifacts are not automatically compliance-grade records.

Implementation meaning:

- Export supports ad hoc delivery or download use cases.
- Export is not a substitute for governed approval publication.

### `publish`

`publish` is the governed operation that creates approved publication artifacts.

Requirements:

- `publish` can only occur after full dialectic validation.
- `publish` MUST be blocked unless the dialectic validator passes all required gates.
- `publish` MUST persist both Markdown and JSON artifacts in `prd_output/`.
- `publish` MUST use the `canonical_model` as the source for both persisted formats.
- `publish` MUST be the only operation that establishes approval-grade PRD artifacts.
- `publish` MUST be treated as distinct from `preview`, `emit`, and ad hoc `export`.

Implementation meaning:

- Publish is not just returning content to a caller.
- Publish is the governed transition from validated internal state to approved persisted artifacts.

### `approved_publication`

`approved_publication` is the post-approval state produced by a successful `publish` operation.

Requirements:

- `approved_publication` MUST refer to a PRD that has passed full dialectic validation and has been published through the governed path.
- `approved_publication` MUST include persisted Markdown and JSON artifacts in `prd_output/`.
- `approved_publication` MUST be traceable to the validated `canonical_model`.

Implementation meaning:

- `approved_publication` is an outcome state, not just a display format.
- An approved publication is defined by governance and persistence, not by whether a user saw a rendered view.

## Lifecycle contexts

The system MUST support and distinguish the following three lifecycle contexts.

### `pre_approval_preview`

Definition:

- A pre-publication review context used before approval.

Rules:

- Source of truth MUST remain the `canonical_model`.
- The system MAY `render` Markdown, JSON, or both.
- The system MAY `emit` rendered content to the client.
- The system MUST NOT treat emitted preview content as approval-grade persistence.
- The system SHOULD avoid writing approval-grade artifacts.
- The system MUST NOT treat this context as `approved_publication`.

Decision outcome:

- Client-visible output is allowed.
- Compliance-grade persistence is not established.

### Example — `pre_approval_preview`

- Requested view: `json_only`
- Effective emitted view: `json_only`
- Persisted artifacts: none required

Interpretation:

- The system may show or return JSON to the caller for review.
- No approval-grade publication artifacts are created in `prd_output/`.
- This remains a preview and MUST NOT be treated as `approved_publication`.

### `approved_publication`

Definition:

- The governed post-approval context entered only through a successful `publish`.

Rules:

- Source of truth MUST remain the `canonical_model`.
- The system MUST perform `render` from the `canonical_model` into Markdown and JSON.
- The system MAY `emit` status, artifact references, and/or rendered content to the client.
- The system MUST `persist` both Markdown and JSON artifacts in `prd_output/`.
- The system MUST require full dialectic validation before allowing publication.
- The system MUST treat persisted dual-format artifacts as the approval-grade record.

Decision outcome:

- Client-visible output may occur, but is secondary.
- Compliance-grade persistence is mandatory.

### Example — `approved_publication`

- Requested view: `markdown_only`
- Effective emitted view: `markdown_only`
- Persisted artifacts: `prd_output/example-prd.md` and `prd_output/example-prd.json`

Interpretation:

- The caller may receive only the Markdown response view.
- The system MUST still persist both `.md` and `.json` artifacts in `prd_output/`.
- Single-format selection remains a response-shaping choice only and cannot weaken approved-publication persistence.

### `ad_hoc_export`

Definition:

- A non-governed delivery context used to provide requested representations outside the approved publication path.

Rules:

- Source of truth MUST remain the `canonical_model`.
- The system MAY `render` Markdown, JSON, or both.
- The system MAY `emit` exported content to the client.
- The system MAY `persist` export artifacts if the feature requires it.
- The system MUST NOT classify ad hoc exports as `approved_publication`.
- The system MUST NOT imply that exported artifacts satisfy publication governance requirements.

Decision outcome:

- Client-visible output is allowed.
- Persistence, if any, is convenience-oriented rather than approval-grade.

### Example — `ad_hoc_export`

- Requested view: `markdown_only`
- Effective emitted view: `markdown_only`
- Persisted artifacts: none required

Interpretation:

- The caller may receive a Markdown export for convenience.
- The export remains distinct from governed `publish` behavior.
- Export semantics MUST NOT be treated as sufficient for approved-publication persistence.

## Authoritative decision contract

The following rules are mandatory.

### 1. Source-of-truth rule

The `canonical_model` remains the sole source of truth at every lifecycle stage.

Corollaries:

- Markdown is not the source of truth.
- JSON output is not the source of truth.
- Preview payloads are not the source of truth.
- Exported files are not the source of truth.
- Persisted approved artifacts are records derived from the source of truth, not replacements for it.

### 2. Render rule

`render` produces Markdown and/or JSON views from the `canonical_model`.

Corollaries:

- Rendering is a transformation step.
- Rendering does not decide visibility.
- Rendering does not decide durability.
- Rendering does not by itself create an approved publication.

### 3. Emit rule

`emit` controls what is returned or displayed to the client.

Corollaries:

- An API response, stream, CLI display, or UI preview is governed by `emit`.
- Client-visible output may differ by context.
- Emission is not equivalent to persistence.
- Emission is never sufficient on its own to satisfy approval-grade artifact requirements.

### 4. Persist rule

`persist` controls what is written as durable artifacts.

Corollaries:

- Approval-grade persistence requirements are stricter than preview behavior.
- The system must distinguish convenience writes from governed records.
- A persisted artifact is only an approved publication artifact when produced by `publish` under the governed rules.

### 5. Separation rule: client-visible output vs compliance-grade persistence

The system MUST explicitly separate client-visible emitted view from compliance-grade persistence requirements.

Required interpretation:

- What is shown or returned to the client is governed by `emit`.
- What is written as approval-grade artifacts is governed by `persist`.
- A successful preview or export emission MUST NOT be interpreted as a successful approved publication.
- A successful approved publication requires mandatory persistence behavior beyond any emitted response.
- `markdown_only` and `json_only` are client-visible view/export choices only and cannot weaken approved-publication persistence.

### 6. Publish governance rule

`publish` is the governed operation that transitions a PRD into `approved_publication`.

Mandatory gates:

- Full dialectic validation MUST complete before publish is allowed.
- Publish MUST be blocked unless validation reaches the required threshold.
- Publish MUST be blocked on unresolved contradiction or failed validation checks.
- Publish MUST use the validated `canonical_model`.
- Publish MUST persist both Markdown and JSON artifacts in `prd_output/`.

Evidence expectations:

- The publish path SHOULD produce validation artifacts or logs that demonstrate the dialectic process completed.
- For self-evolution flows, logs or equivalent evidence MUST show `VisionContext.SELF` ingestion consistent with `internal/SELF_VISION.md`.
- Publish-proof events, signed reports, or equivalent attestations MAY be used by enforcement layers, but they do not relax the core contract above.

### 7. Approved-publication record rule

A PRD qualifies as `approved_publication` only if all of the following are true:

- it has passed full dialectic validation,
- it has been processed through `publish`,
- both Markdown and JSON have been persisted in `prd_output/`, and
- those artifacts were derived from the `canonical_model`.

If any condition is missing, the result is not `approved_publication`.

## Required implementation consequences

Implementations MUST preserve the following behavior:

1. Internal PRD state management uses the `canonical_model` as the sole authority.
2. Rendering functions derive Markdown and/or JSON from that model.
3. Response logic uses `emit` to control what a caller sees.
4. Storage logic uses `persist` to control what artifacts are written.
5. Preview and export flows must not be mislabeled as publication.
6. Governed publication must require full dialectic validation before execution.
7. Governed publication must persist both `.md` and `.json` artifacts in `prd_output/`.
8. Approved publication must be represented as a governed state transition, not merely a displayed response.

## Non-compliant examples

The following are explicitly non-compliant:

- Treating a Markdown document as the canonical source of truth after rendering.
- Returning Markdown to a client and calling that event “published” without dual persistence.
- Writing only one approved artifact format during publication.
- Allowing ad hoc export to count as approved publication.
- Collapsing `emit` and `persist` into a single undifferentiated operation.
- Publishing before full dialectic validation has completed and passed.
- Declaring approved publication without artifacts persisted in `prd_output/`.

## Compliance checklist

An implementation conforms to this contract only if all answers are “yes”:

- Is the `canonical_model` the sole source of truth?
- Does `render` derive Markdown and/or JSON from that model?
- Does `emit` govern what is returned or displayed to the client?
- Does `persist` govern what is written durably?
- Are `emit` and `persist` treated as distinct concerns?
- Are the lifecycle contexts `pre_approval_preview`, `approved_publication`, and `ad_hoc_export` explicitly distinguished?
- Is `publish` the governed operation for approved publication?
- Is `publish` blocked until full dialectic validation passes?
- Does `publish` persist both Markdown and JSON to `prd_output/`?
- Is `approved_publication` reserved for successfully governed, dual-format persisted outcomes?
