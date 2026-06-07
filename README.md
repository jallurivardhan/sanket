# Sanket
### The signal between financial minds.

> **Google Cloud Rapid Agent Hackathon 2026**  
> Financial Services Track | Arize Partner

[![Demo](https://img.shields.io/badge/Demo-Live-green)]()
[![License](https://img.shields.io/badge/License-MIT-blue)]()

## What Is Sanket?

$485 billion is lost to financial fraud annually 
because bank AI agents work in isolation. 
Sanket connects them.

A privacy-preserving cross-institutional AI agent 
signal network — when one bank's Gemini agent 
detects fraud, every connected institution knows 
in milliseconds. Zero raw customer data shared.

## Quick Start

```bash
# Clone
git clone https://github.com/jallurivardhan/sanket
cd sanket

# Copy env
cp .env.example .env

# Start with Docker
docker-compose up

# Or run locally
pip install -r backend/requirements.txt
python start.py
# In another terminal:
cd frontend && npm install --legacy-peer-deps && npm run dev
```

## Demo
```bash
# Run fraud detection demo
curl -X POST "http://localhost:8000/api/v1/demo/run?scenario=coordinated_fraud"

# Check health
curl http://localhost:8000/health

# View audit trail
curl http://localhost:8000/api/v1/audit/trail
```

## Architecture

Bank A Agent → [Sanket Protocol] → Bank B Agent
↓                ↓                  ↓
Gemini          Redis <3ms         Gemini
LangGraph       Arize Phoenix      LangGraph
Privacy Filter  Audit Trail        Flag Accounts

## Results
- **3ms** signal routing (with Redis)
- **Zero PII** in any transmitted signal  
- **7 fraud indicators** detected from 
  behavioral patterns alone
- **Full BSA compliance** audit trail

## Tech Stack
Gemini 3.1 Pro · LangGraph · Google Cloud 
Agent Builder · Arize Phoenix · FastAPI · 
Redis · React · Python 3.11

## Team
**Vardhan Jallu** — Senior AI Engineer  
github.com/jallurivardhan/sanket

---
*Built for Google Cloud Rapid Agent Hackathon 2026*
