"""CLI interface."""

import os
import sys

import typer

from sre_agent.agent import SREAgent
from sre_agent.utils import get_logger

app = typer.Typer()
logger = get_logger(__name__)


@app.command()
def diagnose(
    namespace: str = typer.Option("default", "--namespace", "-n"),
    deployment: str = typer.Option(None, "--deployment", "-d"),
    service: str = typer.Option(None, "--service", "-s"),
):
    """Diagnose a Kubernetes resource."""
    # Check for API key
    if not os.getenv("OPENROUTER_API_KEY"):
        typer.echo("❌ Error: OPENROUTER_API_KEY not set", err=True)
        typer.echo("   Run: source scripts/setup_env.sh", err=True)
        typer.echo("   Or: export OPENROUTER_API_KEY='your-key'", err=True)
        sys.exit(1)
    
    try:
        agent = SREAgent()
    except ValueError as e:
        typer.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    
    if deployment:
        result = agent.run(namespace, "Deployment", deployment)
    elif service:
        result = agent.run(namespace, "Service", service)
    else:
        typer.echo("Error: Must specify --deployment or --service", err=True)
        sys.exit(1)
    
    if "error" in result:
        typer.echo(f"\n❌ Error: {result['error']}", err=True)
        typer.echo("\nTroubleshooting:", err=True)
        typer.echo("  1. Check kubectl is configured: kubectl cluster-info", err=True)
        typer.echo("  2. Verify resource exists: kubectl get <resource> <name> -n <namespace>", err=True)
        typer.echo("  3. Check OPENROUTER_API_KEY is set", err=True)
        sys.exit(1)
    
    # Show kubectl status first
    typer.echo("\n" + "="*70)
    typer.echo("KUBERNETES RESOURCE STATUS")
    typer.echo("="*70)
    
    if resource_type.lower() == "deployment":
        typer.echo(f"\n📊 Deployment: {resource_name}")
        import subprocess
        try:
            kubectl_result = subprocess.run(
                ["kubectl", "get", "deployment", resource_name, "-n", namespace, "-o", "wide"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if kubectl_result.returncode == 0:
                typer.echo(kubectl_result.stdout)
            else:
                typer.echo(f"  ⚠️  Could not fetch deployment status")
        except:
            pass
        
        typer.echo(f"\n📊 Pods:")
        try:
            pod_result = subprocess.run(
                ["kubectl", "get", "pods", "-n", namespace, "-l", f"app={resource_name}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if pod_result.returncode == 0:
                typer.echo(pod_result.stdout)
        except:
            pass
    else:
        typer.echo(f"\n📊 Service: {resource_name}")
        try:
            svc_result = subprocess.run(
                ["kubectl", "get", "svc", resource_name, "-n", namespace],
                capture_output=True,
                text=True,
                timeout=5
            )
            if svc_result.returncode == 0:
                typer.echo(svc_result.stdout)
            
            ep_result = subprocess.run(
                ["kubectl", "get", "endpoints", resource_name, "-n", namespace],
                capture_output=True,
                text=True,
                timeout=5
            )
            if ep_result.returncode == 0:
                typer.echo(f"\n📊 Endpoints:")
                typer.echo(ep_result.stdout)
        except:
            pass
    
    typer.echo("\n" + "="*70)
    typer.echo("AI AGENT DIAGNOSIS")
    typer.echo("="*70)
    
    failure_type = result.get('failure_type', 'None')
    if failure_type and failure_type != 'None':
        typer.echo(f"\n🔴 Failure Detected: {failure_type}")
    else:
        typer.echo(f"\n🟢 Status: Healthy (No failures detected)")
    
    if "diagnosis" in result:
        diag = result["diagnosis"]
        typer.echo(f"\n📋 Root Cause Analysis:")
        root_cause = diag.get('root_cause', 'N/A')
        # Wrap long lines
        import textwrap
        for line in root_cause.split('\n'):
            wrapped = textwrap.fill(line, width=65, initial_indent="   ", subsequent_indent="   ")
            typer.echo(wrapped)
        
        factors = diag.get('contributing_factors', [])
        if factors:
            typer.echo(f"\n📝 Contributing Factors:")
            for factor in factors:
                typer.echo(f"   • {factor}")
        
        typer.echo(f"\n📊 Confidence: {diag.get('confidence', 0)}%")
    
    if "proposal" in result:
        prop = result["proposal"]
        typer.echo(f"\n" + "="*70)
        typer.echo("PROPOSED FIX")
        typer.echo("="*70)
        
        fix_cmd = prop.get('fix_command', '')
        if fix_cmd and not fix_cmd.startswith('#'):
            typer.echo(f"\n🔧 kubectl Command:")
            # Format command nicely
            import textwrap
            wrapped_cmd = textwrap.fill(fix_cmd, width=68, initial_indent="   ", subsequent_indent="   ", break_long_words=False, break_on_hyphens=False)
            typer.echo(wrapped_cmd)
            
            typer.echo(f"\n💡 To execute manually:")
            typer.echo(f"   {fix_cmd}")
        else:
            typer.echo(f"\n   {fix_cmd or 'No fix command available'}")
        
        if prop.get('fix_yaml'):
            typer.echo(f"\n📄 YAML Patch:")
            typer.echo(f"   {prop.get('fix_yaml')}")
        
        typer.echo(f"\n⚠️  Risk Level: {prop.get('risk_level', 'N/A').upper()}")
        
        if prop.get('rollback_plan'):
            typer.echo(f"\n↩️  Rollback Plan:")
            rollback = prop.get('rollback_plan')
            import textwrap
            wrapped = textwrap.fill(rollback, width=65, initial_indent="   ", subsequent_indent="   ")
            typer.echo(wrapped)
        
        if prop.get('expected_outcome'):
            typer.echo(f"\n✅ Expected Outcome:")
            outcome = prop.get('expected_outcome')
            import textwrap
            wrapped = textwrap.fill(outcome, width=65, initial_indent="   ", subsequent_indent="   ")
            typer.echo(wrapped)
        
        typer.echo(f"\n" + "="*70)
        typer.echo("EXECUTE FIX")
        typer.echo("="*70)
        if resource_type.lower() == "deployment":
            typer.echo(f"\n   ./scripts/run_agent.sh execute --namespace {namespace} --deployment {resource_name}")
        else:
            typer.echo(f"\n   ./scripts/run_agent.sh execute --namespace {namespace} --service {resource_name}")
        typer.echo(f"\n   Or use: ./scripts/simple_diagnose.sh {namespace} {resource_type} {resource_name}")
    
    if "evaluation" in result:
        eval_result = result["evaluation"]
        typer.echo(f"\n" + "="*60)
        typer.echo("EVALUATION")
        typer.echo("="*60)
        if eval_result.get('fixed'):
            typer.echo(f"✅ Status: FIXED")
        else:
            typer.echo(f"❌ Status: NOT FIXED")
        typer.echo(f"   Details: {eval_result.get('status', 'N/A')}")


@app.command()
def execute(
    namespace: str = typer.Option("default", "--namespace", "-n"),
    deployment: str = typer.Option(None, "--deployment", "-d"),
    service: str = typer.Option(None, "--service", "-s"),
):
    """Execute an approved fix."""
    # Check for API key
    if not os.getenv("OPENROUTER_API_KEY"):
        typer.echo("❌ Error: OPENROUTER_API_KEY not set", err=True)
        typer.echo("   Run: source scripts/setup_env.sh", err=True)
        sys.exit(1)
    
    try:
        agent = SREAgent()
        
        if deployment:
            result = agent.execute_fix(namespace, "Deployment", deployment)
        elif service:
            result = agent.execute_fix(namespace, "Service", service)
        else:
            typer.echo("Error: Must specify --deployment or --service", err=True)
            sys.exit(1)
        
        if "error" in result:
            typer.echo(f"❌ Error: {result['error']}", err=True)
            sys.exit(1)
        
        eval_result = result.get("evaluation", {})
        if eval_result.get("fixed"):
            typer.echo("✅ Fix executed successfully!")
            typer.echo(f"Status: {eval_result.get('status', 'healthy')}")
        else:
            typer.echo("⚠️ Fix executed but issue persists")
            typer.echo(f"Status: {eval_result.get('status', 'unknown')}")
    except ValueError as e:
        typer.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8000, "--port"),
):
    """Start the API server."""
    import uvicorn
    from sre_agent.api import app as api_app
    
    uvicorn.run(api_app, host=host, port=port)


def main():
    app()
