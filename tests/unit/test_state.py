"""Tests for state module."""

from k8s_sre_agent.core.state import ActionStep, create_initial_state


def test_create_initial_state():
    state = create_initial_state("default", "Deployment", "my-app")
    
    assert state["namespace"] == "default"
    assert state["resource_type"] == "Deployment"
    assert state["resource_name"] == "my-app"
    assert state["detected"] is False
    assert state["approval_status"] == "pending"
    assert state["workflow_id"] is not None


def test_action_step():
    step = ActionStep(
        description="Test fix",
        command="kubectl apply -f test.yaml",
        probability=0.85,
        risk_level="safe",
        rollback="kubectl delete -f test.yaml",
    )
    
    assert step.probability == 0.85
    assert step.risk_level == "safe"

