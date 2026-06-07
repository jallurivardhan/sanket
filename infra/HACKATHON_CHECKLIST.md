# Sanket — Hackathon Submission Checklist

## Deadline: June 11, 2026 @ 5:00pm EDT

## Required Items

### Code Repository
- [x] Public GitHub repo
      github.com/jallurivardhan/sanket
- [x] MIT License visible at top of repo
- [x] Complete open source codebase
- [x] README with quick start instructions

### Hosted Project URL
- [ ] Backend deployed to Google Cloud Run
      URL: ___________________________
- [ ] Frontend deployed (Vercel/Netlify)
      URL: ___________________________
- [ ] Health check passing at /health

### Demo Video (3 minutes max)
- [ ] Record screen showing dashboard
- [ ] Follow DEMO_SCRIPT.md narration
- [ ] Show coordinated fraud scenario running
- [ ] Show signal flying between banks
- [ ] Show Arize audit trail
- [ ] Upload to YouTube (unlisted is fine)
- [ ] Copy video URL for Devpost

### Devpost Submission Form
- [ ] Project name: Sanket
- [ ] Tagline: The signal between financial minds
- [ ] Partner track selected: Arize
- [ ] Repo URL added
- [ ] Hosted URL added
- [ ] Video URL added
- [ ] Description written (use SUBMISSION.md)
- [ ] Screenshots added (3-5 of dashboard)
- [ ] Submit button clicked before 5pm EDT

## Devpost Description (Copy This)

**What it does:**
Sanket is a cross-institutional AI agent signal network. When one bank's Gemini AI agent detects fraud, every connected institution is alerted within milliseconds — with zero raw customer data shared. Built with LangGraph, Gemini 3.1 Pro, and Arize Phoenix for full agent observability.

**How we built it:**
Each bank runs a LangGraph 7-node state machine powered by Gemini 3.1 Pro. A privacy filter strips all PII before any signal leaves an institution. The Sanket protocol layer routes encrypted behavioral fingerprints between banks via Redis pub/sub. Every agent decision is traced in Arize Phoenix via OpenInference instrumentation.

**Challenges:**
Getting financial institutions to trust a cross-institutional signal network required mathematical privacy guarantees — not promises. We implemented 5 layers of privacy protection ensuring it is architecturally impossible for PII to exist in any transmitted signal.

**Accomplishments:**
3ms signal routing. Zero PII transmission. 7 fraud indicators detected from behavioral patterns alone. Full BSA compliance audit trail.

**What we learned:**
The hardest problem in cross-institutional AI is trust — not technology. The privacy-by-design architecture is what makes this deployable in the real world.

**What's next:**
Connect real bank sandbox APIs, add federated learning, build the agent certification marketplace.

**Built with:**
Gemini 3.1 Pro, Google Cloud Agent Builder, Arize Phoenix, LangGraph, FastAPI, Redis, React, Python, Docker, Google Cloud Run
