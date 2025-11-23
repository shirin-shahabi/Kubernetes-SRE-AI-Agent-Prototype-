"""
LangChain-based AI Agent for reasoning about Kubernetes issues.
"""
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from typing import Dict, Any
import logging
import os

logger = logging.getLogger(__name__)


class SREAgent:
    """AI Agent using LangChain for reasoning about Kubernetes issues."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize the SRE Agent with LangChain."""
        api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("No OpenAI API key provided. Agent will use rule-based diagnostics only.")
            self.llm = None
        else:
            try:
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model="gpt-3.5-turbo",
                    temperature=0.2,
                    api_key=api_key
                )
                logger.info("Initialized LangChain with OpenAI LLM")
            except Exception as e:
                logger.error(f"Failed to initialize LLM: {e}")
                self.llm = None
    
    def analyze_diagnosis(self, diagnosis: Dict[str, Any]) -> str:
        """
        Use LLM to provide detailed analysis and explanation of the diagnosis.
        
        Args:
            diagnosis: Diagnosis dictionary from diagnostics module
            
        Returns:
            Detailed explanation and recommendations from the LLM
        """
        if not self.llm:
            return self._format_basic_analysis(diagnosis)
        
        prompt_template = PromptTemplate(
            input_variables=["issue_type", "root_cause", "details", "suggested_fix"],
            template="""
You are an expert Site Reliability Engineer analyzing a Kubernetes issue.

Issue Type: {issue_type}
Root Cause: {root_cause}
Details: {details}
Suggested Fix: {suggested_fix}

Provide a clear, concise analysis including:
1. A brief explanation of what went wrong
2. Why this issue occurred
3. The recommended fix and why it will resolve the issue
4. Any additional considerations or best practices

Keep your response focused and actionable for an SRE operator.
"""
        )
        
        try:
            chain = LLMChain(llm=self.llm, prompt=prompt_template)
            response = chain.run(
                issue_type=diagnosis.get('issue_type', 'Unknown'),
                root_cause=diagnosis.get('root_cause', 'Not determined'),
                details=str(diagnosis.get('details', {})),
                suggested_fix=str(diagnosis.get('suggested_fix', {}))
            )
            return response
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return self._format_basic_analysis(diagnosis)
    
    def _format_basic_analysis(self, diagnosis: Dict[str, Any]) -> str:
        """Format a basic analysis without LLM."""
        analysis = f"""
=== SRE Analysis ===

Issue Type: {diagnosis.get('issue_type', 'Unknown')}

Root Cause:
{diagnosis.get('root_cause', 'Not determined')}

Suggested Fix:
{self._format_suggested_fix(diagnosis.get('suggested_fix', {}))}

Additional Details:
{self._format_details(diagnosis.get('details', {}))}
"""
        return analysis
    
    def _format_suggested_fix(self, suggested_fix: Dict[str, Any]) -> str:
        """Format the suggested fix for display."""
        if not suggested_fix:
            return "No automated fix available"
        
        action = suggested_fix.get('action', 'Unknown action')
        
        if action == 'increase_memory_limit':
            return f"""
Action: Increase memory limit
Container: {suggested_fix.get('container_name', 'N/A')}
Current Limit: {suggested_fix.get('current_limit', 'N/A')}
Suggested Limit: {suggested_fix.get('suggested_limit', 'N/A')}
"""
        elif action == 'fix_service_selector':
            return f"""
Action: Fix service selector labels
Current Selector: {suggested_fix.get('current_selector', {})}
Corrected Selector: {suggested_fix.get('suggested_selector', {})}
"""
        
        return str(suggested_fix)
    
    def _format_details(self, details: Dict[str, Any]) -> str:
        """Format details for display."""
        if not details:
            return "No additional details"
        
        formatted = []
        for key, value in details.items():
            formatted.append(f"  {key}: {value}")
        
        return "\n".join(formatted)


# Fix import
from typing import Optional
