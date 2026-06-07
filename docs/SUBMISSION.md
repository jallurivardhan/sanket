# Sanket — Devpost Submission

## Hackathon
Google Cloud Rapid Agent Hackathon 2026
Track: Financial Services
Partner: Arize Phoenix (MCP)

## Tagline
The signal between financial minds.

## The Problem
$485 billion is lost to financial fraud every year.
Not because banks lack AI — but because their AI 
agents work in complete isolation.

A fraudster opens accounts at three banks 
simultaneously. Each bank's AI sees something 
suspicious but cannot tell the others. By the time 
any single institution acts, the fraud is complete.

## What Sanket Does
Sanket is a privacy-preserving cross-institutional 
AI agent signal network.

When Bank A's agent detects fraud, it:
1. Strips all customer PII from the pattern
2. Sends an encrypted behavioral fingerprint 
   through the Sanket protocol layer
3. Bank B's agent receives the signal in <500ms
4. Bank B's Gemini agent evaluates and acts
5. Every decision is traced in Arize Phoenix
6. Full compliance audit trail generated

Zero raw customer data is ever shared.

## How We Built It

### Agent Architecture
- LangGraph 7-node state machine per bank agent
- Gemini 3.1 Pro reasoning for fraud analysis
- Google Cloud Agent Builder for orchestration
- Conditional edges route fraud vs normal flows

### Privacy by Design
- Microsoft Presidio PII detection
- Behavioral fingerprints only — no names, 
  accounts, SSN ever transmitted
- SHA-256 pattern hashing for signal identity
- Privacy validation before every transmission

### Real-time Protocol Layer
- Redis pub/sub for <500ms signal delivery
- FastAPI + WebSocket for live dashboard
- Immutable audit trail with hash chain
- BSA/AML/OFAC compliance checks built in

### Observability (Arize Partner MCP)
- Every agent decision traced via Arize Phoenix
- LangChain auto-instrumentation via OpenInference
- Full span data: reasoning, confidence, actions
- Regulator-ready audit export

## Tech Stack
- Gemini 3.1 Pro (Google Vertex AI)
- Google Cloud Agent Builder
- Arize Phoenix MCP (Partner Integration)
- LangGraph + LangChain
- FastAPI + WebSocket
- Redis pub/sub
- React + Vite dashboard
- Python 3.11 / Pydantic v2
- Docker + Google Cloud Run

## Demo Scenarios
1. Coordinated Multi-Bank Fraud
   Fraudster opens accounts at 2 banks 
   simultaneously. Sanket detects and alerts 
   both institutions in 3ms.

2. Synthetic Identity Attack  
   AI-built fake identity draining accounts.
   Structuring pattern detected, SAR triggered.

3. Normal Baseline
   No fraud. Network monitors normally.

## Results
- Signal routing: 3ms average latency
- Privacy: Zero PII in any transmitted signal
- Compliance: Full BSA audit trail per signal
- Accuracy: Gemini detects 7 fraud indicators
  from behavioral patterns alone

## What's Next
- Connect real bank sandbox APIs (Plaid, MX)
- Add federated learning for shared model training
- Expand to KYC handshake protocol
- Build the agent certification marketplace

## Team
Vardhan Jallu — Senior AI Engineer
GitHub: github.com/jallurivardhan/sanket

---

## Arize Partner Integration Evidence

Arize Phoenix is integrated as follows:

1. observability.py sets up OTLP exporter 
   pointing to app.phoenix.arize.com

2. LangChainInstrumentor() instruments every 
   LangGraph node automatically

3. Every agent span includes:
   - institution_id
   - signal_type  
   - confidence_score
   - action_taken
   - fraud_detected boolean

4. SanketTracer context manager wraps all 
   critical routing operations

5. Audit trail exported via 
   GET /api/v1/audit/trail returns 
   Arize span IDs for cross-reference

---

## Judging Criteria Checklist

✅ Moves beyond chat: Two agents taking real 
   actions — flagging accounts, routing signals, 
   generating SAR triggers

✅ Multi-step mission: 7-node LangGraph pipeline
   monitor → analyze → strip_pii → 
   prepare_signal → process_received → 
   execute_actions → audit

✅ Partner power: Arize Phoenix MCP integrated 
   for full agent observability and audit trail

✅ Real-world problem: $485B fraud problem, 
   real regulatory requirements (BSA, AML, OFAC)

✅ Financial services track: Cross-institutional 
   fraud detection — exactly the stated use case
