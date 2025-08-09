#!/usr/bin/env python3
"""Quick test of the NCO search engine."""

import inference

def main():
    print("Loading NCO engine...")
    engine = inference.NCOEngine()
    print(f"Engine loaded with {engine.num_occupations} occupations")
    
    # Test search
    test_queries = [
        "software engineer",
        "teacher",
        "doctor",
        "mechanic",
        "nurse"
    ]
    
    for query in test_queries:
        print(f"\nSearching for: '{query}'")
        results = engine.search(query, k=3)
        
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['nco_code']}: {result['title']} (score: {result['score']:.3f})")

if __name__ == "__main__":
    main()
