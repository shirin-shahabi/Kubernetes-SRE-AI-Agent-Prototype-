# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Considerations

### Kubernetes Access

- The agent requires read access to Kubernetes resources
- Write access (patch/apply) should be restricted to specific namespaces
- Use RBAC to limit agent permissions
- Never run with cluster-admin privileges

### API Keys

- **Ollama**: No API keys required (local model)
- **OpenAI** (if used): Store API keys in environment variables or secret management
- Never commit API keys to version control

### Network Security

- Qdrant and RabbitMQ should be on private networks in production
- Use TLS for RabbitMQ connections
- Restrict API endpoints with authentication

### Sandbox Execution

- All kubectl commands are validated before execution
- Dry-run is enforced by default
- Commands timeout after 30 seconds
- Only kubectl commands are allowed

### Logging

- No sensitive data (API keys, tokens) in logs
- Logs are stored locally by default
- In production, use secure log aggregation

### Recommendations

1. **Deploy in isolated namespace** with limited RBAC
2. **Use NetworkPolicies** to restrict pod communication
3. **Enable audit logging** for all Kubernetes API calls
4. **Regular security updates** for dependencies
5. **Monitor for suspicious activity** in logs

## Reporting a Vulnerability

Please report security vulnerabilities to: [security@example.com]

Do not open public issues for security vulnerabilities.

