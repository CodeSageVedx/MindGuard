# MindGuard — Architecture

This document describes how the **client**, **API server**, and **AI microservice** fit together; how the **reference design** (therapeutic state machine) relates to the **implemented LangGraph**; and how **RAG**, **memory**, and **safety** layers interact. Diagrams use [Mermaid](https://mermaid.js.org/).

---

## 1. System context

Who talks to whom at the ecosystem boundary.

```mermaid
flowchart TB
    subgraph Users
        U[End user]
    end

    subgraph MindGuard
        WEB[React client]
        API[Express API]
        AI[FastAPI + LangGraph]
        VK[LiveKit voice worker]
    end

    subgraph Data_and_models
        MDB[(MongoDB)]
        QD[(Qdrant)]
        N4J[(Neo4j)]
        LLM[Gemini / OpenAI APIs]
        DG[Deepgram STT/TTS]
        LK[LiveKit Cloud]
    end

    U --> WEB
    U --> LK
    WEB --> API
    API --> MDB
    API -. internal HTTP .-> AI
    VK --> LK
    VK --> DG
    VK --> AI
    AI --> MDB
    AI --> QD
    AI --> N4J
    AI --> LLM
```

**Notes**

- Express persists **users**, **sessions**, and **chat logs** (`Server/src/models`).
- The AI service should be called from a **trusted backend** using `X-Internal-Secret`, not exposed with provider keys to browsers in production.
- Voice: **LiveKit** + **Deepgram**; reasoning in `Server-AI/src/livekit/langgraph_llm.py` and `Server-AI/src/agents/voice_agent.py`.

---

## 2. Container view (logical components)

```mermaid
flowchart LR
    subgraph client["client (Vite + React)"]
        UI[UI shell / future chat]
    end

    subgraph server["Server (Express)"]
        AUTH[OTP + JWT auth]
        SESS[Session lifecycle]
        CHAT[Chat persistence]
    end

    subgraph server_ai["Server-AI (FastAPI)"]
        ROUTES[REST + SSE routes]
        GRAPH[LangGraph app_graph]
        REP[Reporting + sentiment]
        VOICE[LiveKit agent process]
    end

    UI -->|HTTPS| AUTH
    UI -->|HTTPS| SESS
    CHAT -. planned: forward turns .-> ROUTES
    ROUTES --> GRAPH
    ROUTES --> REP
    VOICE --> GRAPH
```

**Integration status**

- `chat.controller.ts` still returns a **placeholder** AI message; wire to `/api/v1/agent/invoke` or `/api/v1/agent/stream`.
- `session.controller.ts` has **TODO** hooks for LiveKit/AI binding and report generation on session end.

---

## 3. Reference design: therapeutic multi-agent graph (problem statement)

The project brief describes a **supervisor-style LangGraph** with **nine functional roles** and **conditional routing** (conceptual). This is the **product/intent** layer—not a line-for-line match to `node.py` names.

```mermaid
stateDiagram-v2
    [*] --> TriageWelcome: User message

    TriageWelcome --> SymptomAssessment: Low acute risk
    TriageWelcome --> CrisisSafety: High risk / crisis cues

    SymptomAssessment --> EmotionValidation: Screening complete
    SymptomAssessment --> CrisisSafety: Escalation

    EmotionValidation --> BreathingGrounding: Anxiety / panic signal
    EmotionValidation --> CognitiveReframing: CBT path
    EmotionValidation --> CopingStrategy: Behavioral activation
    EmotionValidation --> MindfulnessPositivePsych: Resilience path

    CognitiveReframing --> ReferralResource: Needs professional care
    CopingStrategy --> ReferralResource: Needs professional care
    MindfulnessPositivePsych --> ReferralResource: Needs professional care

    BreathingGrounding --> EmotionValidation: Stabilized
    CrisisSafety --> ReferralResource: After safety script
    ReferralResource --> [*]
```

**Reference routing ideas (from brief)**

- Elevated **risk score** → prioritize **Crisis & safety** and **Referral & resource** flows.  
- **Anxiety / panic** signals → **Breathing & grounding** before deeper cognitive work.  
- **Shared state** (conceptual): user id, transcript, emotional/risk summary, visited intents, session duration.

---

## 4. Implemented LangGraph pipeline (Graph A)

Built in `Server-AI/src/agents/graph.py`, compiled with **MongoDB checkpointer** (`langgraph-checkpoint-mongodb`). State: `GraphAState` in `Server-AI/src/agents/state.py`.

### 4.1 Node-level flowchart

```mermaid
flowchart TD
    START([START]) --> RT[risk_triage]
    RT -->|needsCrisis| CO[crisis_override]
    RT -->|else| FA[fast_acknowledge]
    FA --> RD[route_decider]
    RD -->|retrievalNeeded| QF[query_fanout_translate]
    RD -->|else| CC1[counseling_composer]
    QF --> RC[retrieve_context]
    RC --> CPB[context_pack_builder]
    CPB --> SPM[session_phase_manager]
    SPM --> CC2[counseling_composer]
    CC2 -->|phase ended / crisis| CO2[crisis_override]
    CC2 -->|default| SO[stream_out]
    CO --> SO
    CO2 --> SO
    SO --> CAT[checkpoint_and_trace]
    CAT --> END([END])
```

**Node intent**

| Node | Role |
|------|------|
| `risk_triage` | Safety classification; crisis short-circuit. |
| `fast_acknowledge` | Low-latency empathy before heavier steps. |
| `route_decider` | Whether to run retrieval (RAG / memory / graph tools). |
| `query_fanout_translate` | Query generation for heterogeneous stores. |
| `retrieve_context` | Pull into `rag`, `memory`, related slices. |
| `context_pack_builder` | Merge into `contextPack.mergedContext` + `sourcesMeta`. |
| `session_phase_manager` | Phases: `opening` → `working` → `closing` → `ended`. |
| `counseling_composer` | Main reply; may escalate if safety changes. |
| `crisis_override` | Safety-first message path. |
| `stream_out` | Events/tokens for SSE. |
| `checkpoint_and_trace` | Checkpoint + trace metadata. |

> **Note:** `graph.py` registers more than one conditional edge set from `counseling_composer`. Treat the diagram as the **intended** control flow and consolidate edges when evolving the graph.

### 4.2 Mapping: reference nine roles → implemented nodes

```mermaid
flowchart LR
    subgraph ref["Reference roles (brief)"]
        R1[Triage / welcome]
        R2[Symptom assessment]
        R3[Breathing / grounding]
        R4[Emotion validation]
        R5[CBT reframing]
        R6[Coping strategies]
        R7[Mindfulness / positive psych]
        R8[Crisis / safety]
        R9[Referral / resources]
    end

    subgraph impl["Implemented graph"]
        I1[risk_triage]
        I2[fast_acknowledge]
        I3[counseling_composer]
        I4[retrieve_context + context_pack_builder]
        I5[crisis_override]
        I6[session_phase_manager]
    end

    R1 --> I1
    R2 --> I3
    R3 --> I3
    R4 --> I2
    R5 --> I3
    R6 --> I3
    R7 --> I3
    R8 --> I5
    R9 --> I3
    R2 -. evidence .-> I4
    R5 -. evidence .-> I4
```

Therapeutic “modes” in the brief are **composed inside** LLM prompts and routing metadata rather than each being a separate compiled graph node today.

---

## 5. RAG and context (reference vs code)

**Reference pipeline**

```mermaid
flowchart LR
    Q[User query] --> E[Embed query]
    E --> V[Vector search Top-K]
    V --> C[Chunk text + metadata]
    C --> P[Prompt: evidence + policy]
    P --> L[LLM answer]
```

**This repository**

- **Vector DB:** Qdrant (`COLLECTION_NAME`, mem0 collection in `mem0_config.py`).  
- **Embeddings:** OpenAI (`text-embedding-3-small` in mem0 config; RAG stack aligned in agents/tools).  
- **Chunking:** Configure at ingestion time; the brief suggests **512 tokens / 50 overlap** as a baseline for knowledge PDFs.

---

## 6. Risk analysis (reference vs code)

The brief describes a **scoring pipeline** (sentiment models, NER, regex crisis lexicon, weighted score → JSON report). The codebase implements **graph-level triage and override** plus separate **HTTP helpers** (`/analyze/sentiment`, `/analyze/report`). Treat scoring weights in the PDF as **design guidance**; align implementations explicitly when you harden production policy.

```mermaid
flowchart TB
    T[Transcript / turn text] --> S[Sentiment + signals]
    T --> K[Keyword / policy matchers]
    S --> R[Risk level + needsCrisis]
    K --> R
    R -->|critical| C[crisis_override + resources]
    R -->|non-critical| N[Normal counseling path]
```

---

## 7. Request path: non-streaming invoke

```mermaid
sequenceDiagram
    participant C as Caller (Express / tool)
    participant F as FastAPI routes.py
    participant G as LangGraph app_graph
    participant M as Mongo checkpointer
    participant L as LLM + tools

    C->>F: POST /api/v1/agent/invoke + X-Internal-Secret
    F->>F: Build GraphAState from ChatRequest
    F->>G: ainvoke(state, thread_id=sessionId)
    loop Nodes
        G->>L: model / retrieval calls
        G->>M: checkpoint writes
    end
    G-->>F: final state
    F-->>C: ChatResponse (assistantText, riskLevel, route, traceId)
```

---

## 8. Data stores

| Store | Used for |
|-------|-----------|
| **MongoDB** | App data (Mongoose); LangGraph checkpoints (`CHECKPOINT_DB_NAME`). |
| **Qdrant** | Knowledge base + mem0 vector collections. |
| **Neo4j** | mem0 graph store (`mem0_config.py`). |

---

## 9. Security model (baseline)

```mermaid
flowchart LR
    subgraph trusted["Trusted zone"]
        API[Express]
        AI[FastAPI]
    end

    subgraph secrets["Shared secret"]
        H["Header: X-Internal-Secret"]
    end

    API --> H
    H --> AI
```

- Rotate `AI_SERVICE_SECRET` per environment.  
- Never ship provider API keys to the browser.  
- JWT verification: `Server/src/middleware/auth.middleware.ts`.

---

## 10. Related files

| Area | File |
|------|------|
| AI HTTP | `Server-AI/src/api/routes.py` |
| Graph | `Server-AI/src/agents/graph.py` |
| State | `Server-AI/src/agents/state.py` |
| Nodes | `Server-AI/src/agents/node.py` |
| Voice | `Server-AI/src/agents/voice_agent.py` |
| Express | `Server/src/app.ts` |
| Session / chat | `Server/src/controllers/session.controller.ts`, `chat.controller.ts` |
