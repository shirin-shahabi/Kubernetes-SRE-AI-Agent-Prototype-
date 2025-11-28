"""State definitions for the LangGraph workflow."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, TypedDict
import uuid


@dataclass
class ActionStep:
    """A remediation step with probability ranking."""
    description: str
    command: str
    probability: float
    risk_level: Literal["safe", "moderate", "dangerous"] = "moderate"
    rollback: str = ""


class AgentState(TypedDict, total=False):
    """State for LangGraph workflow."""
    namespace: str
    resource_type: str
    resource_name: str
    cluster_state: dict[str, Any]
    failure_type: str | None
    detected: bool
    diagnosis: dict[str, Any] | None
    action_steps: list[dict[str, Any]]
    approval_status: Literal["pending", "approved", "rejected"]
    execution_result: dict[str, Any] | None
    evaluation: dict[str, Any] | None
    error: str | None
    workflow_id: str


def create_initial_state(
    namespace: str, resource_type: str, resource_name: str
) -> AgentState:
    """Create initial workflow state."""
    return AgentState(
        namespace=namespace,
        resource_type=resource_type,
        resource_name=resource_name,
        cluster_state={},
        failure_type=None,
        detected=False,
        diagnosis=None,
        action_steps=[],
        approval_status="pending",
        execution_result=None,
        evaluation=None,
        error=None,
        workflow_id=str(uuid.uuid4()),
    )
