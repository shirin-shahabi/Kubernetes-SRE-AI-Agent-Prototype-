"""
Configuration management for the SRE AI Agent
"""
import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AgentConfig(BaseModel):
    """Configuration for the SRE AI Agent"""
    
    # OpenAI Configuration
    openai_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", ""),
        description="OpenAI API key for LLM"
    )
    
    # Kubernetes Configuration
    kubeconfig_path: Optional[str] = Field(
        default_factory=lambda: os.getenv("KUBECONFIG"),
        description="Path to kubeconfig file"
    )
    
    # Agent Behavior
    dry_run: bool = Field(
        default_factory=lambda: os.getenv("DRY_RUN", "true").lower() == "true",
        description="Whether to run in dry-run mode (no actual remediation)"
    )
    
    log_level: str = Field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"),
        description="Logging level"
    )
    
    # Detection Configuration
    check_interval_seconds: int = Field(
        default=60,
        description="Interval between health checks in seconds"
    )
    
    # Safety Configuration
    max_remediation_attempts: int = Field(
        default=3,
        description="Maximum number of remediation attempts per issue"
    )
    
    require_approval: bool = Field(
        default=True,
        description="Require human approval before remediation"
    )

    class Config:
        validate_assignment = True


# Global configuration instance
config = AgentConfig()
