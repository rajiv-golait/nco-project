# Operations Runbook

This guide covers common operational tasks for the NCO Semantic Search system.

## System Architecture

┌─────────────┐ ┌─────────────
│ Vercel │────▶│ Render │────▶│ FAISS │
│ (Frontend) │ │ (Backend) │ │ (Index) │
└─────────────┘ └─────────────┘ 