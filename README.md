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

1. Create a virtual environment and install Python dependencies:
   `python -m venv .venv` and `pip install -r requirements.txt`
2. Install frontend dependencies:
   `cd frontend && npm install`
3. Start backend:
   `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
4. Start frontend:
   `cd frontend && npm run dev -- --host 0.0.0.0 --port 5173`
5. Open the frontend in the browser.

## Assumptions

- Default behavior works without external AI keys and uses deterministic rule-based responses.
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
