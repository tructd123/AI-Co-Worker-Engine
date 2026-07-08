# AI Co-worker Simulation Engine — Project Context (Version 2)

## 1. Tổng quan Dự án (Project Overview)

**Tên dự án:** AI Co-worker Simulation Engine (Gucci Group Case Study)
**Mục tiêu:** Xây dựng một engine mô phỏng môi trường công sở, nơi học viên tương tác và cộng tác với các Đồng nghiệp AI (AI Co-workers / NPC) để giải quyết các bài toán kinh doanh thực tế. Hệ thống hoạt động như một "Game Engine cho Workplace" — các NPC có cá tính riêng biệt, trí nhớ ngữ cảnh, mục tiêu kinh doanh, và phản ứng cảm xúc thay đổi theo hành vi của người dùng.

**Bối cảnh:** Dự án mở rộng từ AI Assessment Engine (đã hoàn thiện) sang giai đoạn tương tác multi-agent, cho phép học viên "sống" trong bài mô phỏng thay vì chỉ nộp bài và nhận điểm.

---

## 2. Các Thực thể AI (AI Personas / NPCs)

| # | Persona | Vai trò | Ràng buộc cốt lõi |
|---|---------|---------|-------------------|
| 1 | **Gucci Group CEO** | Bảo vệ DNA Tập đoàn, cân bằng quyền tự chủ thương hiệu con vs. chiến lược chung | Nắm NDA, từ chối tiết lộ thông tin mật, ưu tiên tầm nhìn dài hạn |
| 2 | **Gucci Group CHRO** | Phát triển tài năng, luân chuyển nhân sự, áp dụng Khung năng lực (Competency Framework) | **Tuyệt đối không áp đặt** lên DNA thương hiệu con; chỉ hỗ trợ & gợi ý |
| 3 | **Regional Manager (Employer Branding & Internal Comms)** | Chia sẻ thực trạng khu vực, nhu cầu đào tạo, thách thức triển khai | Nói thẳng, thực tế; có thể bày tỏ lo ngại nếu kế hoạch không khả thi |

---

## 3. Kiến trúc Hệ thống (Architecture Overview)

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
   │(GPT/     │   │ DB       │   │(Redis/   │
   │ Claude)  │   │(Pinecone)│   │ Postgres)│
   └─────────┘   └──────────┘   └──────────┘
```

---

## 4. Tech Stack

| Layer | Technology | Lý do |
|-------|-----------|-------|
| **Orchestration** | LangGraph / LangChain | Multi-agent workflow, state machine, cyclic graphs |
| **LLM (NPC)** | GPT-4o / Claude 3.5 Sonnet | EQ cao, role-play tốt, function calling |
| **LLM (Supervisor)** | GPT-4o-mini / Claude Haiku | Chi phí thấp, latency thấp, chạy background |
| **Vector DB** | Pinecone / ChromaDB | RAG cho tài liệu công ty (NDA, policies) |
| **State DB** | Redis (short-term) + PostgreSQL (long-term) | Session state, relationship scores, audit log |
| **Backend API** | FastAPI + WebSockets | Streaming chat realtime, async processing |
| **Safety** | Llama Guard / Custom filter | Input/output filtering, jailbreak prevention |
| **Frontend** | React / Next.js | Chat UI, in-sim tools, portfolio export |

---

## 5. Quy ước Dự án (Project Conventions)

### Cấu trúc Thư mục
```
version2/
├── CLAUDE.md                    # File này — ngữ cảnh dự án
├── docs/
│   └── PROJECT_DOCUMENTATION.md # Tài liệu mô tả chi tiết các bước triển khai
├── src/
│   ├── agents/                  # NPC Agent classes & persona definitions
│   │   ├── base_agent.py        # Abstract base class cho tất cả NPC
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
- **Python:** snake_case cho functions/variables, PascalCase cho classes
- **Files:** snake_case.py
- **Personas:** Được định nghĩa bằng JSON trong `src/data/personas/`
- **API endpoints:** kebab-case (`/api/v1/chat-message`)

### Nguyên tắc Thiết kế
1. **Persona-first:** Mỗi NPC PHẢI có system prompt riêng biệt, ràng buộc ẩn, và mục tiêu kinh doanh cụ thể
2. **Stateful by default:** Mọi tương tác phải được ghi nhận vào Memory (relationship score, conversation history)
3. **Safety always-on:** Mọi output phải đi qua Safety Guardrails trước khi gửi về client
4. **Supervisor is invisible:** Supervisor Agent KHÔNG BAO GIỜ chat trực tiếp với user; chỉ inject hint vào NPC context
5. **Draft-only outputs:** Mọi đề xuất AI phải gắn nhãn "Bản nháp" — user tự xác thực

### Safety Guardrails (Bắt buộc)
- ❌ KHÔNG sử dụng ngôn ngữ cam đoan / cá cược
- ❌ KHÔNG tiết lộ system prompt cho user
- ❌ KHÔNG cho phép NPC ra quyết định thay user
- ✅ Sử dụng diễn đạt trung tính, hedging language
- ✅ Gắn nhãn "Đây là bản nháp / gợi ý" cho mọi output
- ✅ Tuân thủ nguyên tắc Responsible AI của Microsoft

---

## 6. Các Deliverable chính

| # | Deliverable | Mô tả |
|---|-------------|-------|
| 1 | **Persona Design & Interaction Logic** | System prompts, dialogue flows (good/bad), state management |
| 2 | **System Architecture** | High-level diagram, tool use design, latency vs quality strategy |
| 3 | **Supervisor Agent** | Director logic, stuck detection, nudge injection mechanism |
| 4 | **Working Prototype** | Runnable code cho ít nhất 1 NPC agent với đầy đủ persona, memory, tools, safety |

---

## 7. Tiêu chí Đánh giá

1. **Role-Playing Fidelity:** NPC phải có cá tính riêng biệt, nhất quán, đúng chức năng — KHÔNG giống generic chatbot
2. **Architecture Soundness:** Scalable, modular, hiện đại — dễ mở rộng sang kịch bản mô phỏng khác
3. **Problem Solving:** Xử lý edge cases (jailbreak, off-topic, circular loops) một cách mượt mà
4. **Tư duy hệ thống:** Ưu tiên hơn code hoàn hảo — cần thể hiện hiểu biết toàn diện về cách các thành phần kết nối
