#!/usr/bin/env python3
"""Evaluate NCO search quality metrics."""

import argparse
import json
import sys
from typing import List, Dict, Any
import requests
from collections import defaultdict
import numpy as np


def dcg_at_k(relevances: List[float], k: int) -> float:
    """Calculate Discounted Cumulative Gain at k."""
    relevances = relevances[:k]
    if not relevances:
        return 0.0
    
    gains = relevances[0] + sum(
        rel / np.log2(i + 2) for i, rel in enumerate(relevances[1:])
    )
    return gains


def ndcg_at_k(relevances: List[float], k: int) -> float:
    """Calculate Normalized DCG at k."""
    dcg = dcg_at_k(relevances, k)
    ideal_relevances = sorted(relevances, reverse=True)
    idcg = dcg_at_k(ideal_relevances, k)
    
    if idcg == 0:
        return 0.0
    return dcg / idcg


def evaluate_query(api_url: str, query: str, expected_codes: List[str], k: int) -> Dict[str, Any]:
    """Evaluate a single query."""
    # Make search request
    response = requests.post(
        f"{api_url}/search",
        json={"query": query, "k": k}
    )
    response.raise_for_status()
    
    results = response.json()["results"]
    retrieved_codes = [r["nco_code"] for r in results]
    
    # Calculate metrics
    # Recall@k: fraction of relevant items retrieved
    relevant_retrieved = len(set(expected_codes) & set(retrieved_codes[:k]))
    recall = relevant_retrieved / len(expected_codes) if expected_codes else 0
    
    # MRR@k: reciprocal rank of first relevant result
    mrr = 0
    for i, code in enumerate(retrieved_codes[:k]):
        if code in expected_codes:
            mrr = 1 / (i + 1)
            break
    
    # nDCG@k: graded relevance (1 if in expected, 0 otherwise)
    relevances = [1.0 if code in expected_codes else 0.0 for code in retrieved_codes]
    ndcg = ndcg_at_k(relevances, k)
    
    return {
        "query": query,
        "expected": expected_codes,
        "retrieved": retrieved_codes[:k],
        "recall": recall,
        "mrr": mrr,
        "ndcg": ndcg
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate NCO search quality")
    parser.add_argument("--api", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--gold", default="docs/gold.sample.jsonl", help="Gold standard file")
    parser.add_argument("--k", type=int, default=5, help="Top-k results to evaluate")
    parser.add_argument("--output", help="Output file for detailed results")
    
    args = parser.parse_args()
    
    # Load gold standard
    gold_queries = []
    with open(args.gold, "r") as f:
        for line in f:
            gold_queries.append(json.loads(line))
    
    print(f"Evaluating {len(gold_queries)} queries at k={args.k}")
    
    # Evaluate each query
    results = []
    metrics = defaultdict(list)
    
    for gold in gold_queries:
        try:
            result = evaluate_query(
                args.api,
                gold["query"],
                gold["expected_codes"],
                args.k
            )
            results.append(result)
            
            metrics["recall"].append(result["recall"])
            metrics["mrr"].append(result["mrr"])
            metrics["ndcg"].append(result["ndcg"])
            
            print(f"✓ {gold['query']}: R@{args.k}={result['recall']:.2f}, "
                  f"MRR@{args.k}={result['mrr']:.2f}, nDCG@{args.k}={result['ndcg']:.2f}")
        
        except Exception as e:
            print(f"✗ {gold['query']}: Error - {e}")
            results.append({
                "query": gold["query"],
                "error": str(e)
            })
    
    # Calculate aggregate metrics
    aggregate = {
        f"recall@{args.k}": np.mean(metrics["recall"]) if metrics["recall"] else 0,
        f"mrr@{args.k}": np.mean(metrics["mrr"]) if metrics["mrr"] else 0,
        f"ndcg@{args.k}": np.mean(metrics["ndcg"]) if metrics["ndcg"] else 0,
        "num_queries": len(gold_queries),
        "num_evaluated": len(metrics["recall"])
    }
    
    # Print summary
    print("\n" + "="*50)
    print("EVALUATION SUMMARY")
    print("="*50)
    print(json.dumps(aggregate, indent=2))
    
    # Save detailed results if requested
    if args.output:
        output_data = {
            "aggregate": aggregate,
            "queries": results,
            "config": {
                "api": args.api,
                "gold": args.gold,
                "k": args.k
            }
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nDetailed results saved to: {args.output}")
    
    # Exit with error if metrics are too low
    if aggregate[f"recall@{args.k}"] < 0.5:
        print("\nWarning: Recall@{} is below 0.5".format(args.k))
        sys.exit(1)


if __name__ == "__main__":
    main()