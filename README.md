# ClaimSense

ClaimSense is an AI-powered insurance claim explanation assistant designed for the TCS Technology Day challenge. It provides claim status explanations, document validation, guidance retrieval, readiness scoring, and action recommendations using deterministic rules plus optional AI APIs.

## Features

- Conversational claim assistant for health and motor claims
- Claim quick-view status, billing, and next-step recommendations
- Document upload validation with automated mismatch detection
- Coverage and policy guidance retrieval with citations
- Readiness score and checklist for missing items
- Multilingual support for English, Hindi, and Kannada
- Replay mode and sample documents for demo reliability
- SSE-based progress events during claim investigation

## Folder structure

- `backend/`: FastAPI app, data, scripts, and tests
- `frontend/`: Vite + React + TypeScript + Tailwind interface
- `start.ps1` / `start.sh`: helper scripts to launch the app

## Quick start

Start the backend and frontend independently in separate PowerShell terminals.

Backend:

```powershell
cd D:\ClaimSense
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
cd D:\ClaimSense\frontend
npm.cmd install
npm.cmd run dev -- --host 0.0.0.0 --port 5173 --strictPort
```

Open `http://localhost:5173/`. The frontend can render independently; API-backed actions use the Vite `/api` proxy to `http://localhost:8000`.

## Groq configuration

Groq is the primary LLM provider. Create a backend `.env` from the placeholder template and set the API key there; never put it in frontend variables or source files:

```powershell
cd D:\ClaimSense
Copy-Item .env.example .env
# Edit .env and set GROQ_API_KEY to your Groq API key.
```

Backend settings are `GROQ_API_KEY`, `GROQ_BASE_URL`, `FAST_MODEL`, `SMART_MODEL`, `VISION_MODEL`, `FALLBACK_MODEL`, and `REPLAY`. The template provides the Groq API URL and model defaults; override model IDs only with models available to your Groq account. `REPLAY=true` enables replay mode. Without a key, deterministic responses remain available and diagnostics report `not_configured`; check provider connectivity at `http://localhost:8000/api/health/groq`.

## Assumptions

- Deterministic document checks and fallback responses work without external AI keys; live Groq-powered interpretation requires `GROQ_API_KEY`.
- The project intentionally uses JSON-backed synthetic data instead of a database.
- The app keeps claim simulations simple and demo-friendly while still showing realistic insurance flows.

## Agent architecture

The project now follows a lightweight four-agent workflow while keeping the existing FastAPI and React app intact:

- Concierge: detects language, intent, tone, and claim ID; prepares the request and execution plan.
- Claim & Policy Investigator: loads claim facts, policy context, and guidance evidence from the existing mock APIs and RAG pipeline.
- Document Analyst: validates uploaded documents, compares document details against the claim, and separates missing fields from fields that could not be extracted.
- Explainer & Verifier: drafts a response in the customer language, checks citations and claim facts, and rejects unverified output.

Deterministic Python services still handle document requirement mapping, mismatch detection, readiness scoring, deductible calculations, and escalation rules rather than creating separate AI agents.

## Demo

The included sample claims cover health and motor scenarios that surface missing documents, deductible logic, claim readiness gaps, and provider communication recommendations.
