# AI Co-worker Simulation Engine

> **Gucci Group Case Study** — Prototype for an AI Co-worker system in a workplace simulation.

## 🎯 Overview

A workplace simulation engine where learners interact with 3 AI Co-workers (NPCs):
- **Gucci Group CEO** — Strategy, protecting the Group's DNA
- **Gucci Group CHRO** — Human Resources, Competency Framework, talent rotation
- **Regional Manager** — Regional realities, implementation challenges

Each NPC has a distinct personality, memory, business goals, and responses that change based on user behavior.

## � Installation & Usage

```bash
# 1. Clone & navigate
cd version2

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
copy .env.example .env
# Edit .env with your API keys

# 5. Run server
uvicorn src.api.main:app --reload --port 8000
```

## 📁 Project Structure

```
version2/
├── src/
│   ├── agents/          # NPC Agent classes & persona definitions
│   ├── engine/          # Core engine: orchestrator, supervisor, memory, safety
│   ├── tools/           # In-sim tools: KPI calc, A/B test, portfolio export
│   ├── data/            # Persona configs, knowledge base, mock APIs
│   └── api/             # FastAPI endpoints & WebSocket handlers
├── tests/               # Unit & integration tests
├── docs/                # Project documentation
├── requirements.txt     # Python dependencies
└── CLAUDE.md            # Project context configuration
```

## 🔑 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-----------|
| `POST` | `/api/v1/chat` | Send message to NPC |
| `GET` | `/api/v1/personas` | List available NPCs |
| `GET` | `/api/v1/state/{user_id}` | Current session state |
| `POST` | `/api/v1/tools/{tool_name}` | Use in-sim tool |
| `POST` | `/api/v1/export/portfolio` | Export portfolio |
| `WS` | `/ws/chat/{user_id}` | Realtime chat WebSocket |

## ⚙️ Environment Variables

```env
OPENAI_API_KEY=sk-...
URL_ENDPOINT=vtoken.viemind.ai   # OpenAI-compatible host → https://host/v1
# OPENAI_BASE_URL=https://vtoken.viemind.ai/v1  # optional full override
LLM_PROVIDER=openai              # openai | mock
LLM_MODEL=gemini-2.5-flash       # Model for NPC Agent (as exposed by gateway)
LLM_MINI_MODEL=gemini-2.5-flash  # Model for short tasks / Supervisor
REDIS_URL=redis://localhost:6379
```

## 📖 Detailed Documentation

See [ENG_PROJECT_DOCUMENTATION.md](docs/ENG_PROJECT_DOCUMENTATION.md) to fully understand the architecture, persona design, and implementation steps.
