# NCO Search Evaluation Guide

This guide explains how to evaluate the search quality of the NCO semantic search system.

## Metrics

We evaluate the system using three key metrics:

1. **Recall@k**: Fraction of relevant occupations retrieved in top-k results
2. **MRR@k** (Mean Reciprocal Rank): Average of reciprocal ranks of first relevant result
3. **nDCG@k** (Normalized Discounted Cumulative Gain): Measures ranking quality with position-based discounting

## Running Evaluation

### Prerequisites

- Backend API running (default: http://localhost:8000)
- Python environment with requests and numpy

### Basic Evaluation

Using the sample gold standard dataset:

```bash
python scripts/evaluate.py