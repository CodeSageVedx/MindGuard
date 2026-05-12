# MindGuard AI

**Empathetic, stigma-free conversational counselor for accessible mental wellbeing.**

MindGuard AI is a **multi-agent mental health support platform** that combines a **Node.js API**, a **Python AI microservice (FastAPI + LangGraph)**, and a **React client**. It is designed for **safe, session-based conversations** with optional **voice** (LiveKit + Deepgram), **retrieval-augmented** answers (Qdrant), **long-term memory** (mem0), and **graph context** (Neo4j). A **LangGraph** pipeline performs risk triage, routing, context assembly, and crisis-aware response generation with **MongoDB-backed checkpoints**.

---

## Why MindGuard exists (problem statement)

### Scale of the mental health challenge in India

Public health surveys describe a large unmet need for mental health services. The **National Mental Health Survey (NMHS) 2015–16** reported on the order of **~150 million people** in India who could benefit from care—roughly **one in ten adults**—while the **treatment gap** for common mental disorders is often estimated in the **~70–92%** range depending on condition and population. **WHO** burden figures for India highlight substantial **DALYs** and **age-standardized suicide rates** that exceed many regional averages.

### Structural barriers: the “five A’s”

Current systems often fail together on several dimensions:

| Barrier | What goes wrong |
|--------|------------------|
| **Accessibility** | Long travel (e.g. **30–50 km** for many rural households), few nearby clinics. |
| **Affordability** | High private-sector share of care, **out-of-pocket** costs, and financial stress on households. |
| **Availability** | Severe **psychiatrist shortage** (India is far below common **per-100k** benchmarks; rural concentration is worse). |
| **Acceptability** | **Stigma** and fear of discrimination reduce help-seeking. |
| **Awareness** | Low mental health literacy delays recognition and treatment. |

### Human and economic consequences

- **Workforce:** Poor mental wellbeing correlates with large **lost working days** per month compared to healthier peers (order-of-magnitude gaps in survey narratives).  
- **Macro burden:** National analyses have projected **very large cumulative economic losses** from mental health conditions over multi-decade horizons.  
- **Households:** Mental health spending is associated with **poverty transitions** and **catastrophic expenditure** for vulnerable families.  
- **Equity:** Stigma and access issues compound for **women**, **older adults**, **rural communities**, and **marginalized groups**.

MindGuard does **not** “solve” psychiatry shortages by replacing clinicians. It targets the **gap between need and first-line support**: anonymous, **24/7**, **stigma-aware** access to **structured, evidence-informed** conversation and **safety-oriented** escalation guidance.

---

## Proposed solution (how MindGuard helps)

From a product perspective, MindGuard AI is a **multi-agent conversational system** that aims to feel like a **private, supportive companion** while staying within safe boundaries:

- **Conversational counselor (main agent):** LangGraph-orchestrated flow with **risk triage**, **fast acknowledgement**, **retrieval when needed**, and **session phases** (opening → working → closing).  
- **Evidence grounding (RAG):** Retrieval from a curated **knowledge base** (therapy manuals, psychoeducation, clinical references—ingested as chunks in a **vector database**). The reference design uses **512-token chunks** with **overlap**; this repo uses **Qdrant** and **OpenAI embeddings** (see `Server-AI`).  
- **Risk detection & analysis:** Continuous and post-turn **safety signals**, **crisis override** routing, and auxiliary **sentiment / reporting** endpoints for dashboards and session wrap-up.  
- **Multimodal access:** **Web** client (React), **voice** path via **LiveKit** + **Deepgram** STT/TTS, and room for future channels (e.g. messaging integrations described in the proposal).

**Important:** MindGuard is **not** an emergency service, **not** a licensed therapist, and **not** a diagnostic tool. Deployers must provide **human escalation paths**, respect **local regulation**, and run **clinical governance** appropriate to their jurisdiction.

---

## Repository layout

| Path | Role |
|------|------|
| `client/` | Vite + React + Tailwind UI (starter shell). |
| `Server/` | Express 5 API: OTP/JWT auth, sessions, chat persistence (MongoDB/Mongoose). |
| `Server-AI/` | FastAPI: LangGraph agent, SSE streaming, sentiment, reporting, LiveKit voice agent. |

---

## Documentation

| Document | Contents |
|----------|----------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Mermaid diagrams: system context, containers, **reference therapeutic graph**, **implemented LangGraph**, RAG and security. |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | How to contribute, coding conventions, and review expectations. |
| [LICENSE](./LICENSE) | MIT License. |

---

## Prerequisites

- **Node.js** (LTS) for `Server` and `client`  
- **Python 3.11+** for `Server-AI`  
- **MongoDB** (Mongoose + LangGraph checkpoints)  
- **Qdrant** (RAG + mem0 vectors; `Server-AI/docker-compose.yml` runs Qdrant locally)  
- **Neo4j** (mem0 graph store)  
- Provider keys as in `Server-AI/src/config.py` (Gemini, OpenAI, LiveKit, Deepgram, internal `AI_SERVICE_SECRET`, etc.)

---

## Quick start

### 1. AI service (`Server-AI`)

```bash
cd Server-AI
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Configure .env (see Server-AI/src/config.py for required variables)
docker compose up -d        # optional: local Qdrant
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Protected routes expect: `X-Internal-Secret: <AI_SERVICE_SECRET>`.

### 2. API server (`Server`)

```bash
cd Server
npm install
# .env: PORT, MONGODB_URI, CORS_ORIGIN, JWT secrets, etc.
npm run dev
```

### 3. Web client (`client`)

```bash
cd client
npm install
npm run dev
```

---

## Main HTTP surfaces

### Express (`Server`)

| Prefix | Purpose |
|--------|---------|
| `/api/v1/healthcheck` | Health checks |
| `/api/v1/auth` | OTP login, verify, emergency contact, logout |
| `/api/v1/session` | Start / end session |

Chat persistence lives in `Server/src/controllers/chat.controller.ts`. **Integration with the FastAPI agent** is still marked TODO (placeholder assistant text until the backend calls `/api/v1/agent/invoke` or `/api/v1/agent/stream`).

### FastAPI (`Server-AI`)

| Method | Path | Notes |
|--------|------|--------|
| `POST` | `/api/v1/agent/invoke` | Full graph run → assistant text + risk metadata |
| `POST` | `/api/v1/agent/stream` | SSE stream of graph events |
| `POST` | `/api/v1/analyze/report` | Transcript → structured report |
| `POST` | `/api/v1/analyze/sentiment` | Sentiment helper for analytics |

---

## Proposal vs this repository (honest map)

Some items in the problem-statement PDF describe a **target** stack. The **implemented** stack is what you see in code:

| Proposal (document) | Implemented today |
|----------------------|---------------------|
| Chroma or Qdrant | **Qdrant** |
| Redis / PostgreSQL for session + logs | **MongoDB** (Mongoose + checkpoints) |
| WhatsApp / Twilio, offline SQLite | **Not wired** in this repo (roadmap-friendly) |
| 9 named therapeutic nodes | **LangGraph nodes** in `graph.py` (triage, RAG path, phases, crisis)—see [ARCHITECTURE.md](./ARCHITECTURE.md) for a side-by-side view |

---

## Contributing & license

- **[CONTRIBUTING.md](./CONTRIBUTING.md)**  
- **[LICENSE](./LICENSE)** (MIT)
