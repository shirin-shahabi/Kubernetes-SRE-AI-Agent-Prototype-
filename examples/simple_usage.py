"""
Simple example demonstrating how to use the SRE Agent programmatically
"""
import logging
from sre_agent.config import AgentConfig
from sre_agent.agent import SREAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Simple example of using the SRE Agent"""
    
    # Create configuration
    # Note: Make sure OPENAI_API_KEY is set in your environment or .env file
    config = AgentConfig(
        dry_run=True,  # Safe mode - won't make actual changes
        require_approval=True,  # Require approval for high-risk actions
        check_interval_seconds=60
    )
    
    # Initialize the agent
    agent = SREAgent(config)
    
    # Run a single check on the default namespace
    print("Running SRE Agent check...")
    summary = agent.run_once(namespace="default")
    
    # Display results
    print(f"\nResults:")
    print(f"  Issues detected: {summary['issues_detected']}")
    print(f"  Issues diagnosed: {summary['issues_diagnosed']}")
    print(f"  Remediations attempted: {summary['remediations_attempted']}")
    print(f"  Remediations successful: {summary['remediations_successful']}")
    
    # Show details of each issue
    if summary['issues']:
        print("\nIssue Details:")
        for i, action in enumerate(summary['actions'], 1):
            issue = action['issue']
            print(f"\n{i}. {issue['resource_type']}/{issue['resource_name']}")
            print(f"   Type: {issue['failure_type']}")
            
            if 'diagnosis' in action:
                diagnosis = action['diagnosis']
                print(f"   Root Cause: {diagnosis.get('root_cause', 'Unknown')}")
                
                if diagnosis.get('recommendations'):
                    print(f"   Recommendations:")
                    for rec in diagnosis['recommendations'][:3]:
                        print(f"     - {rec}")
            
            if 'remediation_plan' in action:
                plan = action['remediation_plan']
                print(f"   Planned Action: {plan['action']}")
    
    # Get agent status
    status = agent.get_status()
    print(f"\nAgent Status:")
    print(f"  Dry Run: {status['config']['dry_run']}")
    print(f"  Total Remediations in History: {status['remediation_history_count']}")


if __name__ == '__main__':
    main()
