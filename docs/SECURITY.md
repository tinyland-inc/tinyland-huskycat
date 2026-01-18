# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.x     | Yes       |
| 1.x     | No        |

## Reporting a Vulnerability

Report security vulnerabilities privately via email:

**Contact**: jess@tinyland.ai

**Include**:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

**Response Time**: Within 48 hours for acknowledgment, 7 days for assessment.

## Security Practices

### Container Isolation

All validation runs in isolated containers:
- Read-only workspace mounting
- No network access during validation
- Non-root user execution

### Dependency Scanning

- Dependencies scanned via GitLab SAST
- Lock files ensure reproducible builds
- Regular dependency updates

### Secret Management

- No secrets stored in repository
- Environment variables for credentials
- `.env` files gitignored

## Disclosure Policy

We follow responsible disclosure:
1. Report received and acknowledged
2. Vulnerability assessed and confirmed
3. Fix developed and tested
4. Security advisory published
5. Fix released
