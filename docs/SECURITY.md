# Security

This document outlines the security measures implemented in the NCO Semantic Search system.

## Security Headers

All API responses include the following security headers:

- **Strict-Transport-Security**: Forces HTTPS connections with HSTS preload
- **X-Frame-Options**: DENY - Prevents clickjacking attacks
- **X-Content-Type-Options**: nosniff - Prevents MIME type sniffing
- **Referrer-Policy**: no-referrer - Prevents referrer leakage
- **Content-Security-Policy**: Restrictive CSP allowing only self-hosted resources
- **Permissions-Policy**: Disables unnecessary browser features

## Rate Limiting

Rate limits protect against abuse:

- Search endpoint: 60 requests/minute per IP (configurable via `RATE_LIMIT_SEARCH`)
- Admin endpoints: 20 requests/minute per IP (configurable via `RATE_LIMIT_ADMIN`)

When rate limited, the server responds with HTTP 429 and a Retry-After header.

## Request Size Limits

- JSON request bodies are limited to 10KB
- Larger requests receive HTTP 413 (Payload Too Large)

## Admin Authentication

Admin endpoints require authentication when `ADMIN_TOKEN` is set:

- Token must be provided via `x-admin-token` header
- Query parameter `?token=` supported for development only
- Use strong, randomly generated tokens in production

### Rotating Admin Token

1. Generate new token: `openssl rand -base64 32`
2. Update `ADMIN_TOKEN` environment variable
3. Restart the service
4. Update all admin clients with new token

## CORS Configuration

- Configure `CORS_ORIGINS` to allow only your frontend domain in production
- Default `*` is for development only
- Example: `CORS_ORIGINS=https://nco-search.example.com`

## Data Protection

- No personally identifiable information (PII) is stored
- IP addresses are not logged
- User agent logging can be disabled via `DISABLE_UA_LOGGING=true`
- All logs use ISO timestamps without timezone information

## Dependency Security

- Dependencies are pinned to specific versions
- Regular security scanning via GitHub Dependabot
- CI/CD includes security scanning with Bandit and OSV-Scanner

## Deployment Security

### Render
- Use generated `ADMIN_TOKEN` value
- Enable force HTTPS
- Set restrictive CORS origins

### Vercel
- Environment variables are encrypted at rest
- Automatic HTTPS with HSTS
- DDoS protection included

## Reporting Security Issues

Please report security vulnerabilities to: security@example.com

Do not create public GitHub issues for security problems.