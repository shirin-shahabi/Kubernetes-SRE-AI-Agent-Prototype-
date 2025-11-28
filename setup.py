"""Setup script for development installation."""

from setuptools import setup, find_packages

setup(
    name="kubernetes-sre-agent",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    py_modules=["sre_agent.cli", "sre_agent.web", "sre_agent.api"],
    install_requires=[
        "langgraph>=0.2.0",
        "langchain>=0.3.0",
        "langchain-community>=0.3.0",
        "dspy>=2.5.0",
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.32.0",
        "gradio>=5.0.0",
        "qdrant-client>=1.12.0",
        "pika>=1.3.0",
        "kubernetes>=31.0.0",
        "pyyaml>=6.0.2",
        "pydantic>=2.9.0",
        "pydantic-settings>=2.6.0",
        "structlog>=24.4.0",
        "prometheus-client>=0.21.0",
        "typer>=0.12.0",
        "diskcache>=5.6.0",
        "httpx>=0.27.0",
        "openai>=1.0.0",
    ],
)

