# Returns Manager — Architecture

## 1. Overview

The Returns Manager processes customer-return evidence and produces a structured, traceable evidence record.

The current implementation extracts evidence for:
- Identity — whether the returned item matches the ordered SKU/ASIN.
- Completeness — whether expected parts are present.
- Observable physical state — visual evidence such as signs of use or damage.
- Image quality — whether supplied images are usable for evidence.

The vision layer does not assign an Amazon condition grade or automatically choose disposition. Ambiguous cases are moved to review instead of being forced into PASS or FAIL.

Ambiguous cases are moved to review instead of being forced into PASS or FAIL.

## 2. System Architecture

Client
  |
  v
FastAPI /agent
  |
  v
ReturnsAgent
  |
  +--------------------+
  |                    |
  v                    v
VisionProvider     EvidenceContract
  |
  v
GeminiVisionProvider
  |
  v
Gemini multimodal model

## 3. Components

### FastAPI API
src/main.py provides:
- GET /health
- POST /agent

### ReturnsAgent
src/agent/returns_agent.py:
- parses image references and expected parts
- calls the vision provider
- validates evidence references
- applies confidence and contradiction rules
- creates the EvidenceContract
- fails open to UNCERTAIN and REVIEW when analysis fails

### VisionProvider
src/agent/vision_provider.py defines the provider abstraction and structured vision-analysis models.

### GeminiVisionProvider
src/agent/gemini_provider.py implements the vision provider using Gemini. Available local image files are supplied as image bytes in the same request.

### EvidenceContract
src/models/evidence.py stores record ID, organization, subject, images, checks, outcome, overrides, status and audit metadata.

## 4. Data Flow

Return request
    |
    v
Parse images and expected parts
    |
    v
Single vision-provider call
    |
    v
Structured VisionAnalysis
    |
    v
Validate evidence, confidence and contradictions
    |
    v
EvidenceContract
    |
    v
PASS / FAIL / UNCERTAIN

## 5. Uncertainty Handling

UNCERTAIN is used when evidence is insufficient, contradictory, below the confidence threshold, or unsupported by valid image evidence.

The current confidence threshold is 0.60.

Provider failures fail open into UNCERTAIN with REVIEW status.

## 6. Tenancy and Persistence

The database layer uses SQLAlchemy with SQLite.

Persistent return data is scoped by organization_id to maintain tenant isolation.

## 7. Model / Agent Usage

Related visual checks are requested in one model call.

The model extracts observable evidence while the application layer handles validation, uncertainty and evidence-contract construction.

## 8. Engineering Decisions

- VisionProvider keeps the application independent of a specific vision implementation.
- Related visual evidence is processed in one model request.
- Invalid or contradictory evidence is not forced into a confident decision.
- Model or dependency failures preserve the case and move it to review.
- Tenant context is required for persistent data operations.

## 9. Testing

The automated tests cover:
- provider abstraction
- identity checks
- completeness states
- invalid evidence references
- contradictory evidence
- image quality
- provider failures
- malformed provider output
- database tenancy behavior

Current baseline: 20 tests passing.

## 10. Limitations

- Sample photo references are placeholders; actual evaluation images must be supplied separately.
- Sample data is synthetic and is not authoritative Amazon data.
- Ambiguous cases require review rather than forced automation.
- A held-out evaluation set is required for meaningful accuracy measurement.

## 11. Repository Structure

src/
  agent/
    gemini_provider.py
    returns_agent.py
    vision_provider.py
  db/
    crud.py
    database.py
    models.py
  models/
    api.py
    evidence.py
  main.py

tests/
data/
  returns_sample.csv
  README.md
