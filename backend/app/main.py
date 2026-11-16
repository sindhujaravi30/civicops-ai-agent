from uuid import uuid4
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .graph import run_new_request, resume_request
from .models import StartRequest, ApprovalRequest, WorkflowResponse
from .services import get_profile, init_db, list_audit, seed_demo_profile

app = FastAPI(title="CivicOps AI", version="0.1.0",
              description="LangGraph citizen services workflow demo")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    """Initialize the database and seed a demo citizen on application startup."""
    init_db()
    if not get_profile("demo-citizen"):
        seed_demo_profile()

@app.get("/health")
def health():
    """Return a lightweight health check response for the service."""
    return {"status": "ok", "service": "civicops-ai"}

@app.get("/api/profile/{citizen_id}")
def profile(citizen_id: str):
    """Fetch a citizen profile by ID or raise a 404 error if it does not exist."""
    result = get_profile(citizen_id)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result

@app.post("/api/requests", response_model=WorkflowResponse)
def create_request(request: StartRequest):
    """Start a new workflow request for a citizen and return the workflow response."""
    if not get_profile(request.citizen_id):
        raise HTTPException(status_code=404, detail="Profile not found. Try demo-citizen.")
    return WorkflowResponse(**run_new_request(request.citizen_id, request.message, str(uuid4())))

@app.post("/api/requests/{thread_id}/approve", response_model=WorkflowResponse)
def approve_request(thread_id: str, request: ApprovalRequest):
    """Resume a paused workflow using the approval decision captured from the client."""
    try:
        return WorkflowResponse(**resume_request(thread_id, request.approved, request.comment))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to resume workflow: {exc}") from exc

@app.get("/api/audit/{citizen_id}")
def audit(citizen_id: str):
    """Return recent audit events for a given citizen ID."""
    return {"events": list_audit(citizen_id)}
