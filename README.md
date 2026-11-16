# CivicOps AI — LangGraph Citizen Services Workflow

A locally runnable portfolio project demonstrating a moderately complex agentic workflow for a simulated vehicle-registration renewal.

## What it demonstrates
- LangGraph state, conditional routing, checkpointing and human-in-the-loop interrupts.
- Multi-stage workflow: intent classification → policy retrieval → profile validation → risk assessment → action planning → approval → mock execution → audit.
- FastAPI backend, React/Vite UI, SQLite tools and optional Groq inference.
- Deterministic business rules: the LLM never decides eligibility or performs a transaction.

> Demo only. It uses synthetic data and a mock registry. It does not connect to government systems, accept payments or provide official policy advice.

## Architecture

```text
Citizen UI → FastAPI → LangGraph
                         ├─ classify_intent
                         ├─ retrieve_policies (local knowledge base)
                         ├─ validate_profile (SQLite tool)
                         ├─ assess_risk
                         ├─ create_plan
                         ├─ approval_gate (interrupt + checkpoint)
                         ├─ execute (mock registry tool) OR reject
                         └─ audit (SQLite)
```

## Run locally (Windows PowerShell)

Backend:
```powershell
cd backend
uv sync
Copy-Item .env.example .env
uv run python -m app.seed
uv run uvicorn app.main:app --reload --port 8000
```

Frontend, in another terminal:
```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and submit the prefilled request. Review the action plan and approve or reject the simulated transaction. API docs: http://127.0.0.1:8000/docs.

No API key is required. Optional Groq intent extraction can be enabled in `backend/.env`:
```env
GROQ_API_KEY=your_key
GROQ_MODEL=openai/gpt-oss-20b
USE_LLM_CLASSIFIER=true
```
The project falls back to deterministic classification if the model is unavailable. Groq uses an OpenAI-compatible API endpoint; see https://console.groq.com/docs/openai.

## API
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/profile/{citizen_id}` | Read synthetic profile |
| POST | `/api/requests` | Start workflow |
| POST | `/api/requests/{thread_id}/approve` | Resume paused workflow |
| GET | `/api/audit/{citizen_id}` | Read audit trail |

Demo profile: `demo-citizen`, vehicle `AUH-12345`.

Example:
```powershell
curl.exe -X POST http://127.0.0.1:8000/api/requests -H "Content-Type: application/json" -d "{\"citizen_id\":\"demo-citizen\",\"message\":\"I need to renew my vehicle registration. My insurance expires in 10 days.\"}"
```
Use the returned `thread_id` with the approval endpoint and `{"approved":true}`.

## Why LangGraph?
This is not a single chatbot prompt. Each node has a bounded responsibility and contributes structured data to shared state. Conditional edges route missing or high-risk cases away from execution. `interrupt()` pauses before the mock transaction, and `Command(resume=...)` resumes the checkpoint after a human decision. A tool boundary keeps side effects out of the reasoning nodes.

## Next milestones
1. Inspect graph state and add tracing.
2. Add English/Arabic policy documents and localized responses.
3. Replace lexical retrieval with `sentence-transformers` embeddings + Chroma or PostgreSQL/pgvector.
4. Replace `InMemorySaver` with a PostgreSQL LangGraph checkpointer.
5. Add idempotency keys, bounded retries, notification outbox and role-based approval.
6. Add evaluation datasets for intent routing, retrieval quality and policy-grounded answers.
7. Add Docker/Kubernetes after local development is stable.

## Open-source references
- LangGraph: https://docs.langchain.com/oss/python/langgraph/overview
- Interrupts / human approval: https://docs.langchain.com/oss/python/langgraph/interrupts
- Persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- FastAPI: https://fastapi.tiangolo.com/
- Pydantic: https://docs.pydantic.dev/
- Chroma: https://docs.trychroma.com/
- sentence-transformers: https://www.sbert.net/
- PostgreSQL: https://www.postgresql.org/
- pgvector: https://github.com/pgvector/pgvector
- React: https://react.dev/
- Vite: https://vite.dev/

## Interview pitch
"I built a citizen-services workflow using LangGraph instead of a single prompt chain. It classifies a request, retrieves policy evidence, validates a synthetic profile through tools, assesses risk and creates an action plan. Before a transaction, it pauses using LangGraph's interrupt mechanism. A human can approve or reject, and the graph resumes from its checkpoint. Execution is isolated in a mock tool and every outcome is auditable."
