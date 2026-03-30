# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | Yes                |

## Reporting a Vulnerability

I take security seriously. If you discover a security vulnerability, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please email **ravidhu.dissa@gmail.com** with:

- A description of the vulnerability
- Steps to reproduce the issue
- The affected version(s)
- Any potential impact you have identified

### What to expect

I will do my best to acknowledge, investigate, and fix security issues as quickly as possible. I will coordinate with you on public disclosure timing and credit reporters unless anonymity is requested.

## Scope

The following are in scope for security reports:

- SQL injection through Qraft's templating engine (`ref()`, `source()`, `{{ var }}`)
- Path traversal via model file resolution or config loading
- Arbitrary code execution through macro expansion
- Credential exposure through config, `.env` handling, or logs
- Dependency vulnerabilities in Qraft's direct dependencies

The following are out of scope:

- Vulnerabilities in database engines themselves (DuckDB, PostgreSQL, MySQL, Trino)
- Issues requiring physical access to the machine running Qraft
- Social engineering attacks

## Best Practices for Users

- Never commit `.env` files or database credentials to version control
- Use environment variables for sensitive connection parameters
- Review macro code from third-party sources before use
- Keep Qraft and its dependencies up to date
