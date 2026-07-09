# AI Co-worker Simulation Engine — Project Context

## 1. Project Overview

**Project Name:** AI Co-worker Simulation Engine (Gucci Group Case Study)
**Objective:** Build a workplace simulation engine where learners interact and collaborate with AI Co-workers (NPCs) to solve real-world business problems. The system acts as a "Game Engine for the Workplace" — NPCs have distinct personalities, contextual memory, business goals, and emotional responses that change based on user behavior.

**Context:** The project expands from the AI Assessment Engine (already completed) to a multi-agent interactive phase, allowing learners to "live" in the simulation rather than just submitting assignments and receiving grades.

---

## 2. AI Entities (AI Personas / NPCs)

| # | Persona | Role | Core Constraints |
|---|---------|---------|-------------------|
| 1 | **Gucci Group CEO** | Protect the Group's DNA, balance brand autonomy vs. common strategy | Bound by NDA, refuses to disclose confidential information, prioritizes long-term vision |
| 2 | **Gucci Group CHRO** | Talent development, personnel rotation, applying the Competency Framework | **Absolutely no imposing** on subsidiary brand DNA; only supports & suggests |
| 3 | **Regional Manager (Employer Branding & Internal Comms)** | Share regional realities, training needs, implementation challenges | Direct, practical; may express concerns if plans are unfeasible |

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      FRONT-END                          │
│  (Chat UI + In-Sim Tools: KPI Calc, A/B Test, Export)   │
└──────────────────────┬──────────────────────────────────┘
                       │ WebSocket / REST API
┌──────────────────────▼──────────────────────────────────┐
│              ORCHESTRATION LAYER                         │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Agent Router │  │ Safety Layer │  │ Session Manager│  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
│         │               │                   │            │
│  ┌──────▼───────────────▼───────────────────▼────────┐  │
│  │              NPC AGENT ENGINE                      │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │  │
│  │  │ Persona  │  │ Memory   │  │ Tool Executor    │ │  │
│  │  │ Registry │  │ Manager  │  │ (RAG, Mock APIs) │ │  │
│  │  └──────────┘  └──────────┘  └──────────────────┘ │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │       SUPERVISOR AGENT (Director / Hidden)        │   │
│  │  Goal Tracking · Stuck Detection · Nudge Inject   │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌─────────┐   ┌──────────┐   ┌──────────┐
   │ LLM API │   │ Vector   │   │ State DB │
   │(GPT/     │   │ DB       │   │(Pinecone)│   │ Postgres)│
   └─────────┘   └──────────┘   └──────────┘
```

---

## 4. Tech Stack

| Layer | Technology | Reason |
|-------|-----------|-------|
| **Orchestration** | LangGraph / LangChain | Multi-agent workflow, state machine, cyclic graphs |
| **LLM (NPC)** | GPT-4o / Claude 3.5 Sonnet | High EQ, good role-play, function calling |
| **LLM (Supervisor)** | GPT-4o-mini / Claude Haiku | Low cost, low latency, background execution |
| **Vector DB** | Pinecone / ChromaDB | RAG for company documents (NDA, policies) |
| **State DB** | Redis (short-term) + PostgreSQL (long-term) | Session state, relationship scores, audit log |
| **Backend API** | FastAPI + WebSockets | Realtime streaming chat, async processing |
| **Safety** | Llama Guard / Custom filter | Input/output filtering, jailbreak prevention |
| **Frontend** | React / Next.js | Chat UI, in-sim tools, portfolio export |

---

## 5. Project Conventions

### Directory Structure
```
version2/
├── CLAUDE.md                    # This file — project context
├── docs/
│   └── PROJECT_DOCUMENTATION.md # Detailed implementation documentation
├── src/
│   ├── agents/                  # NPC Agent classes & persona definitions
│   │   ├── base_agent.py        # Abstract base class for all NPCs
│   │   ├── ceo_agent.py         # Gucci Group CEO persona
│   │   ├── chro_agent.py        # Gucci Group CHRO persona
│   │   └── regional_manager.py  # Regional Manager persona
│   ├── engine/                  # Core engine components
│   │   ├── orchestrator.py      # Agent Router & message orchestration
│   │   ├── supervisor.py        # Supervisor/Director agent (hidden)
│   │   ├── memory_manager.py    # State management & conversation memory
│   │   └── safety_guardrails.py # Input/output safety filters
│   ├── tools/                   # In-sim AI tools
│   │   ├── kpi_calculator.py    # KPI simulation tool
│   │   ├── ab_testing.py        # A/B testing simulator
│   │   ├── portfolio_export.py  # One-click portfolio generator
│   │   └── suggestion_library.py# Title & disclaimer suggestions
│   ├── data/                    # Mock data & persona configs
│   │   ├── personas/            # JSON persona definitions
│   │   ├── knowledge_base/      # Company docs for RAG
│   │   └── mock_apis/           # Simulated JIRA, etc.
│   └── api/                     # FastAPI endpoints
│       ├── main.py              # App entrypoint
│       ├── routes/              # API route handlers
│       └── websocket.py         # WebSocket chat handler
├── tests/                       # Unit & integration tests
├── requirements.txt             # Python dependencies
└── README.md                    # Setup & run instructions
```

### Naming Conventions
- **Python:** snake_case for functions/variables, PascalCase for classes
- **Files:** snake_case.py
- **Personas:** Defined in JSON under `src/data/personas/`
- **API endpoints:** kebab-case (`/api/v1/chat-message`)

### Design Principles
1. **Persona-first:** Each NPC MUST have a distinct system prompt, hidden constraints, and specific business goals
2. **Stateful by default:** All interactions must be recorded in Memory (relationship score, conversation history)
3. **Safety always-on:** All outputs must pass through Safety Guardrails before being sent to the client
4. **Supervisor is invisible:** The Supervisor Agent NEVER chats directly with the user; it only injects hints into the NPC context
5. **Draft-only outputs:** All AI proposals must be labeled "Draft" — the user verifies them

### Safety Guardrails (Mandatory)
- ❌ DO NOT use guaranteeing / betting language
- ❌ DO NOT reveal the system prompt to the user
- ❌ DO NOT allow NPCs to make decisions on behalf of the user
- ✅ Use neutral phrasing, hedging language
- ✅ Label "This is a draft / suggestion" for all outputs
- ✅ Adhere to Microsoft Responsible AI principles

---

## 6. Key Deliverables

| # | Deliverable | Description |
|---|-------------|-------|
| 1 | **Persona Design & Interaction Logic** | System prompts, dialogue flows (good/bad), state management |
| 2 | **System Architecture** | High-level diagram, tool use design, latency vs quality strategy |
| 3 | **Supervisor Agent** | Director logic, stuck detection, nudge injection mechanism |
| 4 | **Working Prototype** | Runnable code for at least 1 NPC agent with full persona, memory, tools, and safety |

---

## 7. Evaluation Criteria

1. **Role-Playing Fidelity:** NPCs must have distinct, consistent personalities and proper functions — NOT like generic chatbots
2. **Architecture Soundness:** Scalable, modular, modern — easy to expand to other simulation scenarios
3. **Problem Solving:** Handle edge cases (jailbreak, off-topic, circular loops) smoothly
4. **Systems Thinking:** Prioritized over perfect code — must demonstrate a comprehensive understanding of how components connect
