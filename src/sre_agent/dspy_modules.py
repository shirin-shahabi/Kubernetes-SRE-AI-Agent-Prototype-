"""DSPy modules for structured SRE operations."""

import dspy
from typing import List


class DiagnoseSignature(dspy.Signature):
    """Diagnose Kubernetes failure and provide root cause analysis."""
    
    cluster_state: str = dspy.InputField(desc="Kubernetes resource state as JSON")
    failure_type: str = dspy.InputField(desc="Type of failure: OOMKilled or ServiceMisconfigured")
    similar_patterns: str = dspy.InputField(desc="Similar patterns from knowledge base", default="")
    
    root_cause: str = dspy.OutputField(desc="Detailed root cause analysis")
    contributing_factors: List[str] = dspy.OutputField(desc="List of contributing factors")
    evidence: List[str] = dspy.OutputField(desc="Evidence from cluster state")
    confidence: int = dspy.OutputField(desc="Confidence level 0-100")


class ProposeFixSignature(dspy.Signature):
    """Propose a safe remediation fix."""
    
    failure_type: str = dspy.InputField(desc="Type of failure")
    root_cause: str = dspy.InputField(desc="Root cause analysis")
    cluster_state: str = dspy.InputField(desc="Current cluster state")
    
    fix_command: str = dspy.OutputField(desc="kubectl command to fix the issue")
    fix_yaml: str = dspy.OutputField(desc="YAML patch if applicable", default="")
    risk_level: str = dspy.OutputField(desc="Risk level: low, medium, or high")
    rollback_plan: str = dspy.OutputField(desc="How to rollback if fix fails")
    expected_outcome: str = dspy.OutputField(desc="Expected state after fix")


class DiagnoseModule(dspy.Module):
    """DSPy module for diagnosis."""
    
    def __init__(self):
        super().__init__()
        self.diagnose = dspy.ChainOfThought(DiagnoseSignature)
    
    def forward(self, cluster_state: str, failure_type: str, similar_patterns: str = "") -> dspy.Prediction:
        """Perform diagnosis."""
        return self.diagnose(
            cluster_state=cluster_state,
            failure_type=failure_type,
            similar_patterns=similar_patterns,
        )


class ProposeFixModule(dspy.Module):
    """DSPy module for proposing fixes."""
    
    def __init__(self):
        super().__init__()
        self.propose = dspy.ChainOfThought(ProposeFixSignature)
    
    def forward(self, failure_type: str, root_cause: str, cluster_state: str) -> dspy.Prediction:
        """Propose fix."""
        return self.propose(
            failure_type=failure_type,
            root_cause=root_cause,
            cluster_state=cluster_state,
        )

