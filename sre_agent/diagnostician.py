"""
Diagnosis module using LLM for intelligent analysis
"""
import logging
from typing import Dict, Any, Optional

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    from langchain.chat_models import ChatOpenAI

try:
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:
    from langchain.schema import HumanMessage, SystemMessage

from .detector import Issue

logger = logging.getLogger(__name__)


class Diagnostician:
    """Uses LLM to diagnose Kubernetes issues"""
    
    def __init__(self, api_key: str):
        """
        Initialize the diagnostician
        
        Args:
            api_key: OpenAI API key
        """
        self.llm = ChatOpenAI(
            temperature=0.3,
            model_name="gpt-3.5-turbo",
            openai_api_key=api_key
        )
        logger.info("Diagnostician initialized with LLM")
    
    def diagnose(self, issue: Issue, additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Diagnose an issue using LLM reasoning
        
        Args:
            issue: The detected issue
            additional_context: Additional context like logs, events, etc.
            
        Returns:
            Diagnosis dictionary with root cause and recommendations
        """
        logger.info(f"Diagnosing issue: {issue}")
        
        # Prepare context
        context = self._prepare_context(issue, additional_context)
        
        # Create diagnosis prompt
        prompt = self._create_diagnosis_prompt(context)
        
        try:
            # Get diagnosis from LLM
            messages = [
                SystemMessage(content="""You are an expert Kubernetes SRE with deep knowledge of 
                container orchestration, cloud-native applications, and debugging distributed systems.
                Your task is to analyze Kubernetes issues and provide clear, actionable diagnoses."""),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm(messages)
            
            # Parse response
            diagnosis = self._parse_diagnosis(response.content, issue)
            
            logger.info(f"Diagnosis completed: {diagnosis.get('root_cause', 'Unknown')}")
            return diagnosis
            
        except Exception as e:
            logger.error(f"Failed to diagnose issue: {e}")
            return {
                "root_cause": "Unable to determine root cause",
                "explanation": str(e),
                "recommendations": [],
                "confidence": "low"
            }
    
    def _prepare_context(self, issue: Issue, additional_context: Optional[Dict[str, Any]]) -> str:
        """Prepare context for diagnosis"""
        context = f"""
Issue Type: {issue.failure_type.value}
Resource: {issue.resource_type}/{issue.resource_name}
Namespace: {issue.namespace}
Severity: {issue.severity}
Details: {issue.details}
"""
        
        if additional_context:
            if "logs" in additional_context:
                context += f"\n\nRecent Logs:\n{additional_context['logs'][:1000]}"
            
            if "events" in additional_context:
                context += f"\n\nRecent Events:\n"
                for event in additional_context.get("events", [])[:5]:
                    context += f"- {event.get('type')}: {event.get('reason')} - {event.get('message')}\n"
        
        return context
    
    def _create_diagnosis_prompt(self, context: str) -> str:
        """Create diagnosis prompt for LLM"""
        prompt = f"""
Analyze the following Kubernetes issue and provide a detailed diagnosis:

{context}

Please provide:
1. Root Cause: What is the underlying problem?
2. Explanation: Why is this happening?
3. Recommendations: What specific actions should be taken to resolve this? (List 2-3 actionable steps)
4. Confidence Level: How confident are you in this diagnosis? (high/medium/low)

Format your response as:
ROOT_CAUSE: [root cause]
EXPLANATION: [detailed explanation]
RECOMMENDATIONS:
- [recommendation 1]
- [recommendation 2]
- [recommendation 3]
CONFIDENCE: [confidence level]
"""
        return prompt
    
    def _parse_diagnosis(self, response: str, issue: Issue) -> Dict[str, Any]:
        """Parse LLM response into structured diagnosis"""
        diagnosis = {
            "root_cause": "",
            "explanation": "",
            "recommendations": [],
            "confidence": "medium",
            "issue": issue.to_dict()
        }
        
        try:
            lines = response.strip().split("\n")
            current_section = None
            
            for line in lines:
                line = line.strip()
                
                if line.startswith("ROOT_CAUSE:"):
                    diagnosis["root_cause"] = line.replace("ROOT_CAUSE:", "").strip()
                    current_section = None
                elif line.startswith("EXPLANATION:"):
                    diagnosis["explanation"] = line.replace("EXPLANATION:", "").strip()
                    current_section = "explanation"
                elif line.startswith("RECOMMENDATIONS:"):
                    current_section = "recommendations"
                elif line.startswith("CONFIDENCE:"):
                    diagnosis["confidence"] = line.replace("CONFIDENCE:", "").strip().lower()
                    current_section = None
                elif line.startswith("-") and current_section == "recommendations":
                    diagnosis["recommendations"].append(line.lstrip("- ").strip())
                elif current_section == "explanation" and line:
                    diagnosis["explanation"] += " " + line
            
            # Ensure we have at least basic information
            if not diagnosis["root_cause"]:
                diagnosis["root_cause"] = f"Issue with {issue.resource_type}: {issue.failure_type.value}"
            
            if not diagnosis["recommendations"]:
                diagnosis["recommendations"] = ["Manual investigation required"]
                
        except Exception as e:
            logger.error(f"Failed to parse diagnosis: {e}")
            diagnosis["root_cause"] = f"Parsing error: {str(e)}"
        
        return diagnosis
