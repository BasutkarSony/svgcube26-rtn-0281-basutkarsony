# Returns Manager — Evaluation

## 1. Current Automated Evaluation

The implementation was validated with the project's automated test suite.

**Result: 20 passed**

The tests cover:

- Tenant isolation and organization-scoped data access
- Vision provider abstraction
- Single provider request behavior
- Structured vision output
- Identity PASS / FAIL / UNCERTAIN handling
- Completeness states: PRESENT / ABSENT / NOT_VISIBLE
- Invalid evidence references
- Contradictory evidence
- Confidence threshold handling
- Poor image quality
- Provider failures
- Malformed provider output
- Fail-open routing to human review

## 2. Decision and Uncertainty Policy

The agent does not force a decision when evidence is insufficient.

A check becomes `UNCERTAIN` when:
- evidence references are invalid or missing
- confidence is below the configured threshold
- evidence contains contradictory verdicts
- image quality prevents reliable observation
- the vision provider fails
- provider output cannot be validated

An overall uncertain result is routed to `review`.

## 3. Evidence Traceability

Each confident observation is required to reference one or more supplied image indices.

The evidence contract records:
- record and organization identifiers
- supplied image references
- check key
- verdict
- confidence
- supporting detail
- overall outcome
- review status

Invalid evidence references are not accepted as sufficient support for an automated verdict.

## 4. Model Usage

All supplied return images are sent to the vision provider in one analysis request.

The provider is isolated behind the `VisionProvider` interface so the model implementation can be replaced without changing the Returns Agent decision layer.

## 5. Held-Out Visual Evaluation

The repository's sample return data contains placeholder image references rather than an actual labelled image set. Therefore, this implementation does **not** claim visual accuracy, precision, recall, false-positive rate, or false-negative rate from that sample data.

A valid held-out evaluation should use at least 50 unseen return units where applicable, with two independent human labels per unit.

For each important check, the evaluation should report:

| Metric | Report |
|---|---|
| Identity | PASS / FAIL / UNCERTAIN + human agreement |
| Completeness | PASS / FAIL / UNCERTAIN + human agreement |
| Condition evidence | Observation agreement |
| Disposition | Human/policy decision agreement |
| False positives | Count and rate |
| False negatives | Count and rate |
| UNCERTAIN / review rate | Count and percentage |
| Failure modes | Categorized examples |
| Latency | Per-request and batch latency |
| Cost | Model/API cost per unit |

## 6. Known Evaluation Limitation

The current repository does not contain the required labelled held-out visual dataset. No visual accuracy number is reported here to avoid presenting synthetic/sample data as ground truth.

The automated test suite therefore validates engineering behavior and uncertainty handling, while a separate labelled image evaluation is required to measure real vision decision quality.
