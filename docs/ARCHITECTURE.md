# Sanket — System Architecture

## Overview
Sanket is a cross-institutional AI agent signal 
network for financial fraud detection.

## System Flow

Bank A Agent          Sanket Protocol      Bank B Agent
────────────          ───────────────      ────────────
Monitor txns    →     Validate signal  →   Receive alert
Detect fraud          Route to target      Gemini decides
Strip all PII         Log audit trail      Flag accounts
Send signal           <500ms delivery      Confirm back

## Component Architecture

### Bank Agent (LangGraph)

State Machine: 7 nodes
monitor → analyze → strip_pii →
prepare_signal → process_received →
execute_actions → audit
Gemini 3.1 Pro: fraud analysis reasoning
Privacy Filter: PII detection + stripping
Arize Phoenix: full decision tracing

### Sanket Protocol Router

Redis pub/sub: real-time signal delivery
Privacy check: validate before every route
Compliance: BSA/AML/OFAC automatic screening
Audit trail: immutable append-only log
Dashboard events: WebSocket broadcast

### Privacy Architecture

Layer 1: PII key detection (35 forbidden keys)
Layer 2: Regex pattern matching (SSN, email, phone)
Layer 3: Behavioral extraction (aggregate only)
Layer 4: SHA-256 fingerprint hashing
Layer 5: Final validation before transmission

### API Layer

REST:      /health, /network/stats,
/institutions, /audit/trail,
/demo/run, /demo/scenarios
WebSocket: /ws/live (real-time signal feed)

## Security Model
- TLS for all connections
- Zero raw PII in any signal
- JWT authentication (production)
- Rate limiting per institution
- Immutable audit chain

## Performance
- Signal routing: 3ms with Redis
- Agent processing: ~4s with mock Gemini
- Agent processing: ~1s with real Gemini 3.1 Pro
- WebSocket latency: <50ms

## Tech Stack
| Layer | Technology |
|-------|-----------|
| LLM | Gemini 3.1 Pro (Vertex AI) |
| Orchestration | LangGraph |
| Deployment | Google Cloud Agent Builder |
| Observability | Arize Phoenix (Partner MCP) |
| API | FastAPI + WebSocket |
| Real-time | Redis pub/sub |
| Privacy | Presidio PII Detection |
| Frontend | React + Vite |
| Database | PostgreSQL (audit persistence) |
| Infrastructure | Docker + Cloud Run |
