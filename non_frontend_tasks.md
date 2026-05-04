# Non-Frontend Tasks Backlog
Tasks derived from V0 user feedback (`notes_from_v0.md`) requiring backend, LLM, or infrastructure changes. Assigned to respective teams for future implementation.

## Task 1: Explain decision context terms and values to users
- **Team**: LLM
- **Source**: V0 feedback point 12
- **Description**: Explain "chase" strategy and upside/downside numbers in decision outputs. LLM layer must generate clear, user-friendly explanations for these terms and values.

## Task 2: Document or implement MOQ calculation logic
- **Team**: Backend
- **Source**: V0 feedback point 7
- **Description**: Clarify if MOQ is a computed value or user constraint. Update backend logic to document or correctly calculate MOQ as needed.

## Task 3: Show total cost, budget remaining in $M, add risk quantification
- **Team**: Backend
- **Source**: V0 feedback point 5
- **Description**: Compute total cost and budget remaining, display in $M (e.g., $12.1M cost, $5M budget remaining). Add risk quantification (markdown risk or sales loss risk or both) to optimization output.

## Task 4: Update season percentage labels and computation
- **Team**: Backend
- **Source**: V0 feedback point 8
- **Description**: Update pre/in/end season percentage computation. Change "markdown %" label to "end of season %" in outputs.

## Task 5: Add input validation and guidance for what-if scenario inputs
- **Team**: LLM
- **Source**: V0 feedback point 11
- **Description**: Handle unexpected/non-sensical inputs (e.g., "yo bro") in what-if scenarios. LLM layer should reject invalid inputs and return guidance on supported query types.

## Task 6: Add support for selecting multiple categories
- **Team**: Backend
- **Source**: V0 feedback point 1
- **Description**: Allow users to select multiple categories. Backend must accept multiple category inputs and return aggregated or per-category optimization results.

## Task 7: Add support for multiple departments per category
- **Team**: Backend
- **Source**: V0 feedback point 2
- **Description**: Allow users to select multiple departments within a category. Backend must handle multi-department inputs and return combined optimization results.

## Task 8: Add SKU-level policy view on request
- **Team**: Backend
- **Source**: V0 "what more" suggestion 1
- **Description**: Support SKU-level policy view when requested by the user. Backend must enable SKU-level optimization output.

## Task 9: Build approve policy feature with downstream integration
- **Team**: Infra, Backend
- **Source**: V0 "what more" suggestions 2 and 3
- **Description**: Add policy approval workflow. Integrate with downstream systems (Kafka, PO creation tools) to send approved policies and initial purchase orders (units/dollars) to enterprise systems.
