# Security Policy

## Supported Versions

Only the current release receives security fixes. No LTS versions are maintained.

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

## Reporting a Vulnerability

**Please do not open a public issue for security vulnerabilities.**

Use [GitLab confidential issues](https://gitlab.com/genealogy-mcp/gedcom-mcp/-/issues/new?confidential=true)
to report any vulnerability confidentially.

### What to expect

- **Acknowledgement:** within 7 days of submission.
- **Coordinated disclosure window:** 90 days from acknowledgement. We will work with
  you to develop and release a fix before any public disclosure.
- **If accepted:** a patched release will be published and you will be credited in the
  changelog (unless you prefer to remain anonymous).
- **If declined:** you will receive a clear explanation of why the report does not
  qualify as a security vulnerability in this project.

### Scope

This server runs locally and parses GEDCOM files from the local filesystem. Reports
relevant to path traversal, file size denial-of-service, injection vulnerabilities in
tool inputs, data leakage in MCP responses (e.g. full file paths), or malformed GEDCOM
input handling are in scope.
