#!/usr/bin/env python3
"""Build FAISS index from NCO occupation data."""

import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss
from tqdm import tqdm


def load_nco_data():
    """Load NCO data from JSON file."""
    # Try multiple paths depending on where script is run from
    data_files = [
        Path("backend/nco_data.json"),      # From project root
        Path("../backend/nco_data.json"),   # From embeddings/ directory
        Path("nco_data.json"),              # If in backend directory
        Path("backend/nco_data_full.json"), # Fallback to full dataset
        Path("../backend/nco_data_full.json")
    ]
    
    for data_file in data_files:
        if data_file.exists():
            print(f"Loading data from {data_file}")
            with open(data_file, "r", encoding="utf-8") as f:
                return json.load(f)
    
    raise FileNotFoundError("No NCO data file found!")


def create_passage(occupation):
    """Create passage text for embedding."""
    # Support both old 'code' and new 'nco_code' fields
    code_field = occupation.get("nco_code", occupation.get("code"))
    
    # Prefer richer 'search_text' if present (already curated by ETL)
    if occupation.get("search_text"):
        return f"passage: {occupation['search_text']}"

    parts = [
        f"passage: {occupation['title']}",
        occupation.get("description", "")
    ]

    if occupation.get("synonyms"):
        parts.append(f"Synonyms: {', '.join(occupation['synonyms'])}")

    if occupation.get("examples"):
        parts.append(f"Examples: {', '.join(occupation['examples'])}")

    return " ".join(parts)


def build_index(model_name="intfloat/multilingual-e5-small"):
    """Build FAISS index from occupation data."""
    print(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    
    # Load data
    occupations = load_nco_data()
    print(f"Loaded {len(occupations)} occupations")
    
    # Create passages
    passages = [create_passage(occ) for occ in occupations]
    
    # Generate embeddings in batch
    print("Generating embeddings...")
    embeddings = model.encode(
        passages,
        batch_size=64,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True
    )
    
    embeddings = embeddings.astype(np.float32)
    print(f"Embeddings shape: {embeddings.shape}")
    
    # Create FAISS index (using Inner Product since vectors are normalized)
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    
    # Save index and metadata - handle different run locations
    output_paths = [
        Path("backend/faiss_index"),    # From project root
        Path("../backend/faiss_index")  # From embeddings/ directory
    ]
    
    output_dir = None
    for path in output_paths:
        try:
            path.mkdir(parents=True, exist_ok=True)
            output_dir = path
            break
        except:
            continue
    
    if output_dir is None:
        raise RuntimeError("Could not create output directory")
    
    # Save FAISS index
    faiss.write_index(index, str(output_dir / "nco.index"))
    print(f"Saved FAISS index to {output_dir / 'nco.index'}")
    
    # Save metadata
    metadata = {
        "model": model_name,
        "num_occupations": len(occupations),
        "embedding_dim": dimension,
        "occupations": occupations
    }
    
    with open(output_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"Saved metadata to {output_dir / 'meta.json'}")
    
    print("Index building complete!")


if __name__ == "__main__":
    build_index()