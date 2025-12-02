"""CLI for K8s SRE Agent."""

import json

import typer

from k8s_sre_agent.core.agent import SREAgent
from k8s_sre_agent.utils.config import load_config
from k8s_sre_agent.utils.logging import setup_logging

app = typer.Typer(help="Kubernetes SRE AI Agent")


@app.command()
def diagnose(
    namespace: str = typer.Option("default", "-n", "--namespace"),
    resource_type: str = typer.Option(..., "-t", "--type", help="Deployment or Service"),
    resource_name: str = typer.Option(..., "-r", "--resource"),
    auto_approve: bool = typer.Option(False, "--auto-approve", help="Skip approval"),
):
    """Diagnose a Kubernetes resource."""
    load_config()
    setup_logging()
    
    agent = SREAgent()
    
    if auto_approve:
        result = agent.run(namespace, resource_type, resource_name)
    else:
        result = agent.run_until_approval(namespace, resource_type, resource_name)
        
        if result.get("detected"):
            typer.echo(f"\nFailure: {result.get('failure_type')}")
            typer.echo(f"Root Cause: {result.get('diagnosis', {}).get('root_cause')}")
            
            steps = result.get("action_steps", [])
            if steps:
                typer.echo(f"\nProposed Fix: {steps[0]['command']}")
                
                if typer.confirm("Approve and execute?"):
                    result = agent.resume_with_approval(result, approved=True)
                    eval_r = result.get("evaluation", {})
                    typer.echo(f"Result: {'Fixed' if eval_r.get('fixed') else 'Still failing'}")
        else:
            typer.echo("No failure detected")
    
    typer.echo(json.dumps(result, indent=2))


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8000, "--port"),
):
    """Start the REST API server."""
    import uvicorn
    from k8s_sre_agent.api.app import app as api_app
    
    load_config()
    setup_logging()
    uvicorn.run(api_app, host=host, port=port)


@app.command()
def ui(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(7860, "--port"),
):
    """Start the Gradio UI."""
    import os
    
    from k8s_sre_agent.ui.app import create_app
    
    load_config()
    setup_logging()
    
    # Check API key before starting
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        typer.echo("❌ ERROR: OPENROUTER_API_KEY not set!", err=True)
        typer.echo("Please set it with:", err=True)
        typer.echo("  export OPENROUTER_API_KEY='your-key'", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"✅ Starting UI on http://{host}:{port}")
    typer.echo("Press Ctrl+C to stop")
    
    gradio_app = create_app()
    gradio_app.launch(server_name=host, server_port=port, share=False)


def main():
    app()


if __name__ == "__main__":
    main()

