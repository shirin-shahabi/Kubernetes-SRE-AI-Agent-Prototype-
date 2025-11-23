#!/usr/bin/env python3
"""
CLI interface for the SRE AI Agent with human-in-the-loop approval.
"""
import argparse
import logging
import os
import sys
from typing import Optional
from dotenv import load_dotenv

from src.orchestrator import SREOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_separator():
    """Print a visual separator."""
    print("\n" + "="*80 + "\n")


def print_diagnosis_results(result: dict):
    """Pretty print diagnosis results."""
    print_separator()
    print(f"🔍 DIAGNOSIS RESULTS - {result.get('scenario', 'Unknown')}")
    print_separator()
    
    if not result.get('success'):
        print(f"❌ Error: {result.get('error', 'Unknown error')}")
        return
    
    diagnosis = result.get('diagnosis', {})
    
    print(f"📋 Issue Type: {diagnosis.get('issue_type', 'N/A')}")
    print(f"\n🔎 Root Cause:\n{diagnosis.get('root_cause', 'N/A')}")
    
    print(f"\n💡 AI Analysis:\n{result.get('ai_analysis', 'N/A')}")
    
    print_separator()


def get_user_approval(remediation_details: dict) -> bool:
    """
    Get user approval for executing remediation.
    
    Args:
        remediation_details: Details about the proposed remediation
        
    Returns:
        True if user approves, False otherwise
    """
    print("\n🛠️  PROPOSED REMEDIATION")
    print_separator()
    
    suggested_fix = remediation_details.get('diagnosis', {}).get('suggested_fix', {})
    action = suggested_fix.get('action', 'Unknown')
    
    if action == 'increase_memory_limit':
        print(f"Action: Increase Memory Limit")
        print(f"Deployment: {suggested_fix.get('deployment_name')}")
        print(f"Namespace: {remediation_details.get('namespace')}")
        print(f"Container: {suggested_fix.get('container_name')}")
        print(f"Current Limit: {suggested_fix.get('current_limit')}")
        print(f"Proposed Limit: {suggested_fix.get('suggested_limit')}")
    
    elif action == 'fix_service_selector':
        print(f"Action: Fix Service Selector")
        print(f"Service: {suggested_fix.get('service_name')}")
        print(f"Namespace: {remediation_details.get('namespace')}")
        print(f"Current Selector: {suggested_fix.get('current_selector')}")
        print(f"Proposed Selector: {suggested_fix.get('suggested_selector')}")
    
    else:
        print(f"Action: {action}")
        print(f"Details: {suggested_fix}")
    
    print_separator()
    
    while True:
        response = input("\n⚠️  Do you want to apply this fix? (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("Please enter 'yes' or 'no'")


def scenario_oomkilled(orchestrator: SREOrchestrator, namespace: str, deployment: str):
    """Handle Scenario A: OOMKilled Pod."""
    print("\n🚀 Starting Scenario A: OOMKilled Pod Diagnosis")
    print(f"Target: Deployment '{deployment}' in namespace '{namespace}'")
    
    # Step 1: Diagnose
    print("\n📊 Step 1: Diagnosing the issue...")
    result = orchestrator.diagnose_oomkilled_scenario(namespace, deployment)
    
    print_diagnosis_results(result)
    
    if not result.get('success'):
        print("\n❌ Diagnosis failed. Exiting.")
        return
    
    # Step 2: Propose fix and get approval
    print("\n📋 Step 2: Proposing remediation...")
    
    if not result.get('remediation_ready'):
        print("❌ No remediation available.")
        return
    
    # Step 3: Human-in-the-loop approval
    print("\n👤 Step 3: Human approval required...")
    
    approved = get_user_approval(result)
    
    if not approved:
        print("\n⛔ Remediation rejected by operator. No changes made.")
        return
    
    # Step 4: Execute remediation
    print("\n⚙️  Step 4: Executing remediation...")
    
    execution_result = orchestrator.execute_remediation(result)
    
    print_separator()
    if execution_result.get('success'):
        print(f"✅ {execution_result.get('message')}")
        print("\n📝 Remediation Details:")
        print(f"  Action: {execution_result.get('action')}")
        print(f"  Details: {execution_result.get('details')}")
    else:
        print(f"❌ Remediation failed: {execution_result.get('error')}")
    
    print_separator()
    
    # Step 5: Evaluation
    print("\n📈 Step 5: Evaluation")
    print("Please monitor the deployment to verify the fix:")
    print(f"  kubectl get pods -n {namespace} -l app={deployment}")
    print(f"  kubectl describe deployment {deployment} -n {namespace}")


def scenario_broken_service(orchestrator: SREOrchestrator, namespace: str, service: str):
    """Handle Scenario B: Broken Service."""
    print("\n🚀 Starting Scenario B: Broken Service Diagnosis")
    print(f"Target: Service '{service}' in namespace '{namespace}'")
    
    # Step 1: Diagnose
    print("\n📊 Step 1: Diagnosing the issue...")
    result = orchestrator.diagnose_broken_service_scenario(namespace, service)
    
    print_diagnosis_results(result)
    
    if not result.get('success'):
        print("\n❌ Diagnosis failed. Exiting.")
        return
    
    # Step 2: Propose fix and get approval
    print("\n📋 Step 2: Proposing remediation...")
    
    if not result.get('remediation_ready'):
        print("❌ No remediation available.")
        return
    
    # Step 3: Human-in-the-loop approval
    print("\n👤 Step 3: Human approval required...")
    
    approved = get_user_approval(result)
    
    if not approved:
        print("\n⛔ Remediation rejected by operator. No changes made.")
        return
    
    # Step 4: Execute remediation
    print("\n⚙️  Step 4: Executing remediation...")
    
    execution_result = orchestrator.execute_remediation(result)
    
    print_separator()
    if execution_result.get('success'):
        print(f"✅ {execution_result.get('message')}")
        print("\n📝 Remediation Details:")
        print(f"  Action: {execution_result.get('action')}")
        print(f"  Details: {execution_result.get('details')}")
    else:
        print(f"❌ Remediation failed: {execution_result.get('error')}")
    
    print_separator()
    
    # Step 5: Evaluation
    print("\n📈 Step 5: Evaluation")
    print("Please verify the service now has active endpoints:")
    print(f"  kubectl get endpoints {service} -n {namespace}")
    print(f"  kubectl describe service {service} -n {namespace}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Kubernetes SRE AI Agent - Diagnose and remediate common Kubernetes issues',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Diagnose OOMKilled pod scenario
  python cli.py --scenario oomkilled --namespace default --deployment oom-app
  
  # Diagnose broken service scenario
  python cli.py --scenario broken-service --namespace default --service broken-service
        """
    )
    
    parser.add_argument(
        '--scenario',
        required=True,
        choices=['oomkilled', 'broken-service'],
        help='Scenario to diagnose and remediate'
    )
    
    parser.add_argument(
        '--namespace',
        default='default',
        help='Kubernetes namespace (default: default)'
    )
    
    parser.add_argument(
        '--deployment',
        help='Deployment name (required for oomkilled scenario)'
    )
    
    parser.add_argument(
        '--service',
        help='Service name (required for broken-service scenario)'
    )
    
    parser.add_argument(
        '--api-key',
        help='OpenAI API key (optional, can also use OPENAI_API_KEY env var)'
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Validate scenario-specific arguments
    if args.scenario == 'oomkilled' and not args.deployment:
        parser.error("--deployment is required for oomkilled scenario")
    
    if args.scenario == 'broken-service' and not args.service:
        parser.error("--service is required for broken-service scenario")
    
    # Initialize orchestrator
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    
    try:
        orchestrator = SREOrchestrator(openai_api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")
        print(f"\n❌ Error: {e}")
        print("\nPlease ensure you have a valid kubeconfig and access to the cluster.")
        sys.exit(1)
    
    # Execute scenario
    try:
        if args.scenario == 'oomkilled':
            scenario_oomkilled(orchestrator, args.namespace, args.deployment)
        elif args.scenario == 'broken-service':
            scenario_broken_service(orchestrator, args.namespace, args.service)
    except KeyboardInterrupt:
        print("\n\n⛔ Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error during scenario execution: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
