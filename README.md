## NCO Semantic Search v1.0.0

### 🎯 Highlights
- **Multilingual Search**: EN/HI/BN/MR with auto-detection
- **Voice Input**: Hindi-first Web Speech API integration
- **AI-Powered**: E5-small embeddings + FAISS (sub-100ms)
- **Admin Dashboard**: Analytics, logs, synonym management
- **Security**: Token auth, rate limits, CSP, HSTS
- **Privacy**: DPDP-compliant, no PII collection

### 📊 Performance
- Search latency: <100ms (p95)
- Index size: 3.6k occupations
- Memory: ~500MB (model) + 50MB (index)

### 📚 Documentation
- [Demo Script](docs/DEMO.md) - Multilingual query examples
- [Deployment Guide](docs/DEPLOY.md) - Render + Vercel setup
- [API Reference](docs/API.md) - Complete endpoint docs

### 🔒 Security & Compliance
- [Security Policy](docs/SECURITY.md)
- [Privacy Policy](docs/PRIVACY.md)
- [Operations Runbook](docs/OPERATIONS.md)