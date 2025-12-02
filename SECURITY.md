# Security Policy

## Overview

Security is a core design principle of the K8s SRE Agent. Since this agent has the potential to modify Kubernetes clusters, we implement a defense-in-depth strategy to ensure safety, integrity, and access control.

## Security Architecture

### 1. Authentication & Access Control
- **API Key Authentication**: All API endpoints (except health checks) require a Bearer Token.
  - Development: Keys can be generated via `/api-key` (disable in prod).
  - Production: Set `API_SECRET_KEY` env var.
- **RBAC (Future Work)**: We plan to implement Role-Based Access Control to restrict who can approve fixes.

### 2. Human-in-the-Loop Safety Gate
- **No Autonomous Execution**: The agent **never** executes write operations without explicit human approval.
- **Workflow State**: Proposed plans are stored in a pending state until a human reviews and approves them via the UI or API.
- **Feedback Loop**: Human feedback is logged for audit and learning purposes.

### 3. Execution Safety
- **Dry-Run Validation**: All `kubectl` commands are validated with `--dry-run=client` before execution to catch syntax or permission errors safely.
- **Dangerous Command Blocking**: A blocklist prevents execution of destructive commands (e.g., `delete namespace`, `drain node`, `delete all`).
- **Rollback Mechanism**: Every proposed fix is accompanied by a rollback command.

### 4. Network Security
- **Rate Limiting**: API implements in-memory rate limiting (100 requests/minute) to prevent abuse.
- **CORS Policy**: Restricted to localhost UI and specific trusted origins.
- **Sandboxing (Future Work)**: The agent should run in a restricted pod with limited egress and a tightly scoped ServiceAccount.

## Threat Model

| Threat | Mitigation |
|--------|------------|
| **Unauthorized Access** | API Key Auth, future RBAC |
| **Destructive Actions** | Human Approval, Command Blocklist, Dry-Runs |
| **Prompt Injection** | Typed DSPy signatures, Input Validation |
| **DoS Attacks** | Rate Limiting, Timeouts |

## Development Guidelines

- **Secrets**: Never commit secrets. Use environment variables.
- **Dependencies**: Regularly scan dependencies for vulnerabilities.
- **Audit Logs**: Ensure all agent actions and human approvals are logged.

## Reporting Vulnerabilities

Please report security issues to the maintainers directly. Do not open public issues for sensitive vulnerabilities.

