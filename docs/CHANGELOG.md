# Changelog

All notable changes to the NCO Semantic Search project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-20

### Added
- Initial release of NCO Semantic Search system
- Multilingual semantic search using intfloat/multilingual-e5-small embeddings
- Support for English, Hindi, Bengali, and Marathi languages
- Voice search input via Web Speech API
- FAISS-based vector similarity search
- Confidence scoring with low-confidence detection
- Real-time search with debouncing
- Occupation detail pages
- User feedback collection system
- Admin dashboard with analytics
- Synonym management with hot-reload
- Search and feedback logging
- Rate limiting on all endpoints
- Security headers and request size limits
- Prometheus metrics endpoint
- Docker Compose for local development
- Comprehensive test suite
- CI/CD pipelines for GitHub Actions
- Deployment configurations for Render and Vercel

### Security
- Admin authentication via bearer token
- CORS configuration
- CSP headers
- HSTS enforcement
- Request body size limits (10KB)
- Rate limiting (60/min search, 20/min admin)
- Optional user agent logging disable

### Performance
- Sub-100ms search latency
- Batch embedding generation
- In-memory FAISS index
- Efficient JSONL log streaming
- Optimized React components

### Documentation
- API documentation
- Security guidelines
- Privacy policy (DPDP compliant)
- Operations runbook
- Deployment guide
- Demo script with multilingual examples

### Developer Experience
- TypeScript frontend
- Python type hints
- Comprehensive error handling
- Environment-based configuration
- Hot reload in development
- Automated testing