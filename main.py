#!/usr/bin/env python3
"""
Main entry point for the Kubernetes SRE AI Agent
"""
import sys
import logging
import argparse
import json
from typing import Optional

from sre_agent.config import AgentConfig
from sre_agent.agent import SREAgent

# Configure logging
def setup_logging(log_level: str):
    """Setup logging configuration"""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('sre_agent.log')
        ]
    )


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Kubernetes SRE AI Agent - Detect, Diagnose, and Remediate K8s Issues'
    )
    
    parser.add_argument(
        '--namespace',
        type=str,
        default='default',
        help='Kubernetes namespace to monitor (default: default)'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['once', 'continuous'],
        default='once',
        help='Run mode: once for single check, continuous for ongoing monitoring'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Check interval in seconds for continuous mode (default: 60)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (no actual remediation)'
    )
    
    parser.add_argument(
        '--no-approval',
        action='store_true',
        help='Do not require approval for remediations (use with caution!)'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--kubeconfig',
        type=str,
        help='Path to kubeconfig file'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Create configuration
        config = AgentConfig(
            kubeconfig_path=args.kubeconfig,
            dry_run=args.dry_run,
            log_level=args.log_level,
            require_approval=not args.no_approval,
            check_interval_seconds=args.interval
        )
        
        # Validate API key
        if not config.openai_api_key:
            logger.error(
                "OpenAI API key not found. Please set OPENAI_API_KEY environment variable "
                "or add it to .env file"
            )
            sys.exit(1)
        
        # Initialize agent
        logger.info("Initializing SRE AI Agent...")
        agent = SREAgent(config)
        
        # Display configuration
        logger.info(f"Configuration:")
        logger.info(f"  Namespace: {args.namespace}")
        logger.info(f"  Mode: {args.mode}")
        logger.info(f"  Dry Run: {config.dry_run}")
        logger.info(f"  Require Approval: {config.require_approval}")
        
        if args.mode == 'once':
            # Run single check
            logger.info("Running single detection-diagnosis-remediation cycle...")
            summary = agent.run_once(args.namespace)
            
            # Display summary
            print("\n" + "="*60)
            print("SRE AGENT SUMMARY")
            print("="*60)
            print(f"Namespace: {summary['namespace']}")
            print(f"Issues Detected: {summary['issues_detected']}")
            print(f"Issues Diagnosed: {summary['issues_diagnosed']}")
            print(f"Remediations Attempted: {summary['remediations_attempted']}")
            print(f"Remediations Successful: {summary['remediations_successful']}")
            print("="*60)
            
            if summary['issues_detected'] > 0:
                print("\nDetailed Results:")
                for i, action in enumerate(summary['actions'], 1):
                    print(f"\n{i}. {action['issue']['resource_type']}/{action['issue']['resource_name']}")
                    print(f"   Type: {action['issue']['failure_type']}")
                    print(f"   Severity: {action['issue']['severity']}")
                    
                    if 'diagnosis' in action:
                        print(f"   Root Cause: {action['diagnosis'].get('root_cause', 'Unknown')}")
                        print(f"   Confidence: {action['diagnosis'].get('confidence', 'unknown')}")
                    
                    if 'remediation_plan' in action:
                        print(f"   Planned Action: {action['remediation_plan']['action']}")
                        print(f"   Risk Level: {action['remediation_plan']['risk_level']}")
                    
                    if 'remediation_result' in action:
                        result = action['remediation_result']
                        status = "✓ SUCCESS" if result.get('success') else "✗ FAILED"
                        print(f"   Result: {status} - {result.get('message', '')}")
            
            # Save detailed report
            with open('sre_agent_report.json', 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            print("\nDetailed report saved to: sre_agent_report.json")
            
        else:
            # Run continuous monitoring
            logger.info("Starting continuous monitoring...")
            print(f"\nMonitoring namespace '{args.namespace}' every {args.interval} seconds")
            print("Press Ctrl+C to stop\n")
            
            agent.run_continuous(args.namespace, args.interval)
    
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
        print("\nAgent stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
