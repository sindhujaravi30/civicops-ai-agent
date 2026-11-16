import json
import re
from typing import Any
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt, RetryPolicy
from langchain_core.runnables import RunnableConfig
from .models import WorkflowState
from .policy import retrieve_policy
from .services import get_profile, mock_renewal_tool, write_audit
from .settings import settings

def classify_intent(state: WorkflowState) -> dict[str, Any]:
    """Classify the user's request intent and preferred language for the workflow."""
    message = state["user_message"]
    intent = "vehicle_registration_renewal" if any(
        word in message.lower() for word in ("renew", "registration", "vehicle", "car")
    ) else "general_information"
    language = "ar" if re.search(r"[\u0600-\u06FF]", message) else "en"
    if settings.use_llm_classifier and settings.groq_api_key:
        try:
            from langchain_groq import ChatGroq
            from langchain_core.messages import HumanMessage, SystemMessage
            model = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0)
            answer = model.invoke([
                SystemMessage(content='Classify request. Return only JSON: {"intent":"vehicle_registration_renewal" or "general_information","language":"en" or "ar"}.'),
                HumanMessage(content=message),
            ])
            parsed = json.loads(str(answer.content))
            if parsed.get("intent") in ("vehicle_registration_renewal", "general_information"):
                intent = parsed["intent"]
            if parsed.get("language") in ("en", "ar"):
                language = parsed["language"]
        except Exception:
            pass
    return {"intent": intent, "language": language}

def retrieve_policies(state: WorkflowState) -> dict[str, Any]:
    """Retrieve supporting policy excerpts relevant to the citizen's request."""
    return {"policy_evidence": retrieve_policy(state["user_message"] + " vehicle registration insurance fines")}

def validate_profile(state: WorkflowState) -> dict[str, Any]:
    """Check whether the citizen profile contains the required registration details."""
    profile = get_profile(state["citizen_id"])
    if not profile:
        return {"profile": {}, "missing_requirements": ["Citizen profile not found"]}
    missing = []
    if not profile.get("vehicle_id"):
        missing.append("Vehicle identifier")
    if not profile.get("insurance_expiry"):
        missing.append("Valid insurance details")
    return {"profile": profile, "vehicle_id": profile.get("vehicle_id", ""), "missing_requirements": missing}

def assess_risk(state: WorkflowState) -> dict[str, Any]:
    """Determine the operational risk level based on profile and fine status."""
    profile = state.get("profile", {})
    risk = "high" if not profile else ("medium" if profile.get("outstanding_fines", 0) > 0 else "low")
    return {"risk_level": risk}

def create_plan(state: WorkflowState) -> dict[str, Any]:
    """Build a renewal action plan based on the validated citizen profile."""
    profile = state.get("profile", {})
    plan = ["Confirm citizen and vehicle details.",
            "Ensure valid motor insurance for the renewal period.",
            "Review and settle outstanding fines, if applicable.",
            "Submit the renewal request after human approval."]
    if profile.get("insurance_expiry"):
        plan.insert(1, f"Recorded insurance expiry: {profile['insurance_expiry']}. Confirm continuous coverage.")
    return {"action_plan": plan}

def route_after_validation(state: WorkflowState) -> str:
    """Choose the next node after validation based on missing information or risk."""
    if state.get("missing_requirements"):
        return "needs_information"
    if state.get("risk_level") == "high":
        return "blocked"
    return "approval_gate"

def needs_information(state: WorkflowState) -> dict[str, Any]:
    """Report which profile details are missing and require a follow-up update."""
    return {"response": "Please update the missing details: " + ", ".join(state.get("missing_requirements", []))}

def blocked(state: WorkflowState) -> dict[str, Any]:
    """Return a response when the request cannot safely proceed."""
    return {"response": "This request is blocked because the profile could not be safely validated. Contact the relevant service desk."}

def approval_gate(state: WorkflowState) -> dict[str, Any]:
    """Pause the workflow for human approval before any simulated renewal is executed."""
    decision = interrupt({
        "type": "human_approval",
        "message": "Review the proposed simulated vehicle-registration renewal before execution.",
        "citizen_id": state["citizen_id"], "vehicle_id": state.get("vehicle_id"),
        "risk_level": state.get("risk_level"), "action_plan": state.get("action_plan", []),
        "policy_evidence": state.get("policy_evidence", []),
        "notice": "Demo only: no government system will be contacted.",
    })
    approved = decision.get("approved", False) if isinstance(decision, dict) else bool(decision)
    return {"approval": {"approved": approved,
                         "comment": decision.get("comment") if isinstance(decision, dict) else None}}

def route_after_approval(state: WorkflowState) -> str:
    """Continue to execution only when the human approval decision is positive."""
    return "execute" if state.get("approval", {}).get("approved") else "rejected"

def execute(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
    """Execute the simulated vehicle renewal and capture the result for narration."""
    thread_id = config["configurable"]["thread_id"]

    result = mock_renewal_tool(
        state["citizen_id"],
        state["vehicle_id"],
        thread_id
    )

    return {
        "execution_result": result,
        "response": result["message"] + f" Reference: {result['reference']}."
    }

def rejected(state: WorkflowState) -> dict[str, Any]:
    """Return a rejection response when approval is denied."""
    return {"response": "The proposed action was rejected. No simulated renewal was submitted."}

def audit(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
    """Write a final workflow audit event and return the captured state summary."""
    thread_id = config["configurable"]["thread_id"]

    event = {
        "intent": state.get("intent"),
        "risk_level": state.get("risk_level"),
        "approval": state.get("approval"),
        "execution_result": state.get("execution_result")
    }

    write_audit(
        state["citizen_id"],
        thread_id,
        "workflow_completed",
        event
    )

    return {"audit_event": event}

def build_graph():
    """Construct and compile the LangGraph workflow used by the application."""
    builder = StateGraph(WorkflowState)
    builder.add_node("classify_intent", classify_intent)
    builder.add_node("retrieve_policies", retrieve_policies, retry_policy=RetryPolicy(max_attempts=2))
    builder.add_node("validate_profile", validate_profile)
    builder.add_node("assess_risk", assess_risk)
    builder.add_node("create_plan", create_plan)
    builder.add_node("needs_information", needs_information)
    builder.add_node("blocked", blocked)
    builder.add_node("approval_gate", approval_gate)
    builder.add_node("execute", execute)
    builder.add_node("rejected", rejected)
    builder.add_node("audit", audit)
    builder.add_edge(START, "classify_intent")
    builder.add_edge("classify_intent", "retrieve_policies")
    builder.add_edge("retrieve_policies", "validate_profile")
    builder.add_edge("validate_profile", "assess_risk")
    builder.add_edge("assess_risk", "create_plan")
    builder.add_conditional_edges("create_plan", route_after_validation, {
        "needs_information": "needs_information", "blocked": "blocked", "approval_gate": "approval_gate"})
    builder.add_edge("needs_information", END)
    builder.add_edge("blocked", END)
    builder.add_conditional_edges("approval_gate", route_after_approval, {"execute": "execute", "rejected": "rejected"})
    builder.add_edge("execute", "audit")
    builder.add_edge("rejected", "audit")
    builder.add_edge("audit", END)
    return builder.compile(checkpointer=InMemorySaver())

graph = build_graph()

def status_for(state: dict[str, Any], interrupted: bool = False) -> str:
    """Translate the current workflow state into a user-friendly status label."""
    if interrupted: return "approval_required"
    if state.get("execution_result"): return "completed"
    if state.get("approval") and not state["approval"].get("approved"): return "rejected"
    if state.get("missing_requirements"): return "needs_information"
    if state.get("risk_level") == "high": return "blocked"
    return "completed"

def run_new_request(citizen_id: str, message: str, thread_id: str) -> dict[str, Any]:
    """Start a new workflow request and return the state produced by the graph."""
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"citizen_id": citizen_id, "user_message": message}, config)
    paused = bool(result.get("__interrupt__"))
    state = graph.get_state(config).values
    approval = result["__interrupt__"][0].value if paused else None
    return {"thread_id": thread_id, "status": status_for(state, paused),
            "response": state.get("response", "Please review the proposed action."),
            "state": state, "approval_request": approval}

def resume_request(thread_id: str, approved: bool, comment: str | None = None) -> dict[str, Any]:
    """Resume a paused workflow after a human approval or rejection decision."""
    config = {"configurable": {"thread_id": thread_id}}
    graph.invoke(Command(resume={"approved": approved, "comment": comment}), config)
    state = graph.get_state(config).values
    return {"thread_id": thread_id, "status": status_for(state),
            "response": state.get("response", "Workflow finished."),
            "state": state, "approval_request": None}
