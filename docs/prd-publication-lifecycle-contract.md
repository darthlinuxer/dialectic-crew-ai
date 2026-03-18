# PRD Publication Lifecycle Contract

Status: Authoritative  
Audience: Implementers of PRD generation, review, preview, export, and publication workflows  
Scope: PRD output handling and publication decisions

## 1. Purpose

This document is the authoritative lifecycle contract for PRD output handling.

It defines the exact lifecycle terminology and the decision rules that govern:

- the `canonical_model` as the sole source of truth
- how systems `render` client-consumable views
- how systems `emit` a client-visible response
- how systems `persist` approval-grade artifacts
- when behavior is a `preview`
- when behavior is an `export`
- when behavior is a governed `publish`
- what qualifies as an `approved_publication`

This contract is implementation-facing and normative. If any code path, API, or documentation conflicts with this contract, this contract governs.

## 2. Normative terminology

The following terms are required and must be used exactly as defined here.

### 2.1 `canonical_model`

The `canonical_model` is the internal structured PRD representation and remains the sole source of truth for PRD content and state.

Normative rules:

- All PRD lifecycle operations operate from the `canonical_model`.
- No emitted, rendered, exported, or persisted artifact becomes the source of truth over the `canonical_model`.
- Markdown and JSON outputs are derived views or persistence artifacts generated from the `canonical_model`.
- Manual edits to derived artifacts do not redefine or replace the `canonical_model`.

## 3. Derived-output operations

### 3.1 `render`

`render` is the transformation of the `canonical_model` into one or more client-consumable representations.

Normative rules:

- `render` produces Markdown and/or JSON views from the `canonical_model`.
- `render` is a pure derivation step conceptually separate from client delivery and storage decisions.
- `render` does not itself determine whether output is shown to a client or written to durable storage.

Examples:

- Render the current `canonical_model` to Markdown for human review.
- Render the same `canonical_model` to JSON for machine inspection or archival.

### 3.2 `emit`

`emit` controls what is returned or displayed to the client.

Normative rules:

- `emit` is the client-visibility decision.
- `emit` may return Markdown, JSON, both, or a preview-specific subset according to the request and workflow context.
- `emit` does not by itself imply durable storage.
- Client-visible response shape is governed by `emit`, not by `persist`.

### 3.3 `persist`

`persist` controls what is written as approval-grade artifacts.

Normative rules:

- `persist` is the storage decision.
- `persist` writes artifacts to durable storage according to lifecycle context and governance rules.
- Approval-grade persistence requirements are determined independently from the client-facing `emit` choice.
- In governed publication, `persist` must satisfy compliance-grade requirements even when `emit` returns only a single format to the client.

## 4. Client-intent terms

### 4.1 `preview`

A `preview` is a pre-publication, client-visible inspection of rendered output derived from the `canonical_model`.

Normative rules:

- A `preview` is not a governed publication.
- A `preview` may `emit` Markdown, JSON, or both.
- A `preview` does not create an `approved_publication`.
- A `preview` may be non-persistent or may persist only non-approval-grade temporary/supporting data if separately allowed by implementation policy.
- A `preview` must not be treated as fulfillment of publication persistence requirements.

### 4.2 `export`

An `export` is an intentional extraction of rendered output from the `canonical_model` for client use outside the governed publication path.

Normative rules:

- An `export` may occur without approval.
- An `export` may `emit` Markdown, JSON, or both.
- An `export` is not equivalent to `publish`.
- An `export` does not create an `approved_publication` unless it also satisfies the governed publication contract, which ad hoc export does not.

### 4.3 `publish`

`publish` is the governed operation that transitions a PRD into an `approved_publication`.

Normative rules:

- `publish` can only occur after full dialectic validation has completed successfully.
- `publish` is approval-governed, not merely rendering or response delivery.
- `publish` must `persist` both Markdown and JSON artifacts in `prd_output/`.
- `publish` must persist both formats regardless of the requested or emitted client-facing view.
- `publish` is the only operation in this contract that creates an `approved_publication`.

## 5. Publication state term

### 5.1 `approved_publication`

`approved_publication` has two tightly related but distinct senses, and implementations must preserve this distinction to avoid drift:

1. **Lifecycle context sense**: the governed context in which approved publication rules apply.
2. **Resulting artifact/state sense**: the successfully published, approval-grade outcome produced by `publish`.

Normative rules:

- When used as a lifecycle context, `approved_publication` describes the workflow mode and applicable rules.
- When used as a resulting state, `approved_publication` describes the published PRD artifact set and status after successful governed publication.
- Both senses require the same storage requirement: persisted `.md` and `.json` artifacts in `prd_output/`.
- Implementations should name fields, enums, or status values clearly enough to distinguish context from resulting state where ambiguity could occur.

## 6. Explicit lifecycle contexts

The system recognizes exactly these three lifecycle contexts for PRD output handling.

### 6.1 `pre_approval_preview`

`pre_approval_preview` is the context for reviewing or inspecting a PRD before approval-governed publication.

Required behavior:

- Source of truth is the `canonical_model`.
- The system may `render` Markdown, JSON, or both from the `canonical_model`.
- The system may `emit` one or more rendered views to the client.
- The system is not required to `persist` approval-grade artifacts.
- This context must not be treated as `publish`.
- This context must not create an `approved_publication`.

### 6.2 `approved_publication`

`approved_publication` is the governed publication context entered only after successful full dialectic validation and approval.

Required behavior:

- Source of truth remains the `canonical_model`.
- The system may `render` Markdown, JSON, or both from the `canonical_model`.
- The system may `emit` any permitted client-facing view.
- The system must `persist` both `.md` and `.json` artifacts in `prd_output/`.
- The dual-format persistence requirement applies regardless of whether the client requested Markdown only, JSON only, or both.
- This context is executed via `publish`.
- Successful completion yields an `approved_publication` result/state.

### 6.3 `ad_hoc_export`

`ad_hoc_export` is the context for non-governed extraction of PRD views for convenience, tooling, or external consumption outside approved publication.

Required behavior:

- Source of truth is the `canonical_model`.
- The system may `render` Markdown, JSON, or both from the `canonical_model`.
- The system may `emit` one or more rendered views to the client or caller.
- The system may optionally `persist` exported files according to implementation policy, but such persistence is not approval-grade publication persistence unless the governed publication contract is fully satisfied.
- This context is not `publish`.
- This context must not be represented as an `approved_publication`.

## 7. Decision contract: render vs emit vs persist

The publication lifecycle must apply the following decision model.

### 7.1 Source-of-truth rule

Always start from the `canonical_model`.

Decision:

- If PRD content is needed in any output form, first derive it by `render` from the `canonical_model`.

### 7.2 Client-visibility rule

Use `emit` to determine what the client sees.

Decision:

- If the caller asked to view Markdown, `emit` Markdown.
- If the caller asked to view JSON, `emit` JSON.
- If the caller asked for both, `emit` both.
- The emitted response is a delivery choice only and does not define storage obligations.

### 7.3 Persistence rule

Use `persist` to determine what durable artifacts are written.

Decision:

- In `pre_approval_preview`, approval-grade persistence is not required.
- In `ad_hoc_export`, persistence may occur by policy, but that does not constitute governed publication persistence.
- In `approved_publication`, `persist` must write both `.md` and `.json` to `prd_output/`.

### 7.4 Separation rule

Client-visible output and compliance-grade storage are separate decisions.

Normative statement:

- The client-visible emitted view is controlled by `emit`.
- The approval-grade persistence requirement is controlled by `persist`.
- The two decisions must not be conflated.
- A request for a single emitted format does not waive dual-format persistence requirements during `approved_publication`.

## 8. Governed publication requirements

`publish` is governed and must satisfy all of the following:

1. The PRD content originates from the `canonical_model`.
2. Full dialectic validation has completed successfully before publication.
3. The system `render`s publication artifacts from the `canonical_model`.
4. The system may `emit` Markdown, JSON, or both according to client request or API contract.
5. The system must `persist` both Markdown and JSON artifacts.
6. The persisted files must be written into `prd_output/`.
7. Publication succeeds only when both approval-grade artifacts exist in `prd_output/`.
8. A successful governed publication is an `approved_publication`.

Normative invariant:

- Approved publication requires persistence of both `.md` and `.json` in `prd_output/` regardless of requested client-facing view.

## 9. Required implementation interpretation

Implementers must treat these statements as mandatory:

- The `canonical_model` remains the sole source of truth.
- `render` produces Markdown and/or JSON views from that model.
- `emit` controls what is returned or displayed to the client.
- `persist` controls what is written as approval-grade artifacts.
- `preview` is a pre-publication inspection mode and not a governed publication.
- `export` is an ad hoc extraction mode and not a governed publication.
- `publish` is the governed operation and can only occur after full dialectic validation.
- `approved_publication` requires persistence of both formats in `prd_output/`.

## 10. Minimal compliance matrix

| Context | Source of truth | Render allowed | Emit allowed | Approval-grade persist required | Must write `.md` + `.json` to `prd_output/` | Creates `approved_publication` |
|---|---|---|---|---|---|---|
| `pre_approval_preview` | `canonical_model` | Yes | Yes | No | No | No |
| `ad_hoc_export` | `canonical_model` | Yes | Yes | No | No | No |
| `approved_publication` | `canonical_model` | Yes | Yes | Yes | Yes | Yes |

## 11. Non-negotiable invariant

No implementation may treat a client-visible single-format response as sufficient evidence of approved publication.

The only compliant `approved_publication` outcome is one produced by governed `publish` after full dialectic validation, with both Markdown and JSON approval-grade artifacts persisted in `prd_output/`.
