from typing import Any, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

class WorkflowState(TypedDict, total=False):
    """Typed dictionary representing the workflow state passed between graph nodes."""
    citizen_id: str
    user_message: str
    intent: str
    language: str
    vehicle_id: str
    profile: dict[str, Any]
    policy_evidence: list[dict[str, str]]
    missing_requirements: list[str]
    risk_level: str
    action_plan: list[str]
    approval: dict[str, Any]
    execution_result: dict[str, Any]
    audit_event: dict[str, Any]
    response: str

class StartRequest(BaseModel):
    """Request payload used to begin a new workflow for a citizen."""
    citizen_id: str = "demo-citizen"
    message: str = Field(min_length=5, max_length=2000)

class ApprovalRequest(BaseModel):
    """Approval payload that resumes a workflow after human review."""
    approved: bool
    comment: str | None = None

class WorkflowResponse(BaseModel):
    """Response payload returned after processing a workflow request."""
    thread_id: str
    status: Literal["approval_required", "completed", "rejected", "needs_information", "blocked"]
    response: str
    state: dict[str, Any] = {}
    approval_request: dict[str, Any] | None = None
