# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| >= 1.0.0 | ✓ |
| < 1.0.0 | ✗ |

## Reporting a Vulnerability

### Disclosure Process

We take security vulnerabilities seriously. If you discover a security issue, please **do not** create a public issue.

#### How to Report

**Email**: security@yourusername.com

**PGP Key**: (optional - add your PGP key here)

**What to Include**:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if known)

#### Response Timeline

- **Within 48 hours**: Initial response acknowledging receipt
- **Within 7 days**: Assessment and mitigation plan
- **Within 30 days**: Patch release (or status update)
- **Within 90 days**: Public disclosure (with fix)

#### Coordination

We will coordinate with you on:
- Vulnerability confirmation
- Fix development
- Release timing
- Credit attribution

### Security Best Practices for Users

#### API Key Management

1. **Never commit API keys** to version control
2. **Use environment variables** for all sensitive credentials
3. **Rotate keys regularly** (at least quarterly)
4. **Use separate keys** for dev/staging/production
5. **Limit key scopes** to minimum required permissions
6. **Monitor usage** for unusual activity

#### Example Secure Configuration

```bash
# .env file (never commit)
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx

# Add to .gitignore
echo ".env" >> .gitignore
```

#### Code Execution Safety

The `code_execute` tool runs Python code in a sandboxed subprocess. To enhance security:

1. **Network Isolation**: Run in container without internet access
2. **Resource Limits**: Enforce CPU/memory limits
3. **Timeout Enforcement**: Maximum 30s execution (configurable)
4. **Filesystem Sandboxing**: Scoped to `workspace/` directory only

#### Docker Hardening

```yaml
# Use non-root user
USER agentuser

# Read-only root filesystem
--read-only

# Drop capabilities
--cap-drop=ALL

# No privilege escalation
--security-opt=no-new-privileges
```

#### Network Security

1. **HTTPS Only**: Use TLS for all external API calls
2. **Certificate Verification**: Never disable SSL verification
3. **CORS Configuration**: Restrict in production

```python
# production.py
CORS_ORIGINS=["https://yourdomain.com"]
CORS_ALLOW_CREDENTIALS=true
```

### Known Security Considerations

#### Code Execution

The agent can execute Python code via the `code_execute` tool. This is intentionally flexible but requires:

- Run in isolated containers
- Enforce resource limits
- Monitor for abuse
- Consider network isolation

#### File System Access

File I/O tools are scoped to `workspace/` directory. Ensure:

- Directory exists and has proper permissions
- No symlinks escape the workspace
- User permissions are correctly set

#### External API Calls

Agent patterns may make external API calls:

- Monitor for data exfiltration
- Rate limit expensive providers
- Log all tool invocations
- Implement cost alerts

### Dependency Security

We regularly update dependencies for security patches. To check for vulnerabilities:

```bash
pip install safety
safety check

# Or using pip-audit
pip install pip-audit
pip-audit
```

### Environment Variables

#### Required (with defaults)

```bash
# At least one provider required
ANTHROPIC_API_KEY=          # Claude
OPENAI_API_KEY=              # OpenAI
AZURE_OPENAI_API_KEY=        # Azure
GCP_PROJECT_ID=             # GCP
OLLAMA_BASE_URL=             # Ollama (local)

# Optional but recommended
GITHUB_TOKEN=                # For knowledge crawler
```

#### Security Settings

```bash
# Privacy mode - no external API calls
PRIVACY_MODE=false

# Request size limits
MAX_REQUEST_SIZE=10MB
MAX_TOOL_RESULT_SIZE=1MB

# Execution timeout
CODE_EXEC_TIMEOUT=10
```

### Security Audits

This project undergoes periodic security audits:

- **Dependency Scanning**: Automated via GitHub Dependabot
- **Code Scanning**: Automated via GitHub CodeQL
- **Penetration Testing**: Before major releases
- **Bug Bounty**: (coming soon)

### Compliance

This project is designed to support:

- **GDPR**: Data minimization, right to deletion
- **SOC 2**: Audit logging, access controls
- **ISO 27001**: Information security management

### Security Contacts

- **Security Team**: security@yourusername.com
- **Lead Maintainer**: (contact info)
- **Disclosures**: Coordinated via GitHub Security Advisories

### Acknowledgments

We thank all security researchers who help make agentcore-enhanced more secure.

## Policy Last Updated

2025-01-10
