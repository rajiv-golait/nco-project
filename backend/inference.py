import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
import faiss
from sentence_transformers import SentenceTransformer
import langdetect
from langdetect import DetectorFactory

# Make language detection deterministic
DetectorFactory.seed = 42


class NCOEngine:
    def __init__(self, model_name: str = "intfloat/multilingual-e5-small"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        
        # Load FAISS index and metadata
        index_dir = Path("faiss_index")
        if not index_dir.exists():
            raise RuntimeError("FAISS index not found. Run embeddings/build_index.py first.")
        
        self.index = faiss.read_index(str(index_dir / "nco.index"))
        
        with open(index_dir / "meta.json", "r", encoding="utf-8") as f:
            self.metadata = json.load(f)
        
        self.occupations = self.metadata["occupations"]
        self.num_occupations = len(self.occupations)
    
    def embed_query(self, query: str) -> np.ndarray:
        """Embed a query with the 'query:' prefix for E5 model."""
        prefixed_query = f"query: {query}"
        embedding = self.model.encode(prefixed_query, normalize_embeddings=True)
        return embedding.astype(np.float32)
    
    def detect_language(self, text: str) -> str:
        """Detect language of text."""
        try:
            lang = langdetect.detect(text)
            # Map to our supported languages
            lang_map = {
                "en": "en",
                "hi": "hi", 
                "bn": "bn",
                "mr": "mr"
            }
            return lang_map.get(lang, "en")
        except:
            return "en"
    
    def search(self, query: str, k: int = 5) -> List[Dict]:
        """Search for similar occupations."""
        # Embed query
        query_embedding = self.embed_query(query)
        
        # Search in FAISS (using inner product since vectors are normalized)
        distances, indices = self.index.search(
            query_embedding.reshape(1, -1), 
            min(k, self.num_occupations)
        )
        
        # Convert to results
        results = []
        scores = distances[0]
        
        # Calculate softmax for UI confidence
        exp_scores = np.exp(scores - np.max(scores))
        softmax_scores = exp_scores / np.sum(exp_scores)
        
        for idx, (index, score, confidence) in enumerate(zip(indices[0], scores, softmax_scores)):
            if index == -1:  # FAISS returns -1 for unfound
                continue
                
            occupation = self.occupations[index]
            
            # Simple keyword matching for "why matched"
            query_lower = query.lower()
            matched_synonyms = []
            
            # Check title
            if query_lower in occupation["title"].lower():
                matched_synonyms.append(occupation["title"])
            
            # Check synonyms
            for syn in occupation.get("synonyms", []):
                if query_lower in syn.lower() or syn.lower() in query_lower:
                    matched_synonyms.append(syn)
                    if len(matched_synonyms) >= 3:
                        break
            
            # Check examples
            if not matched_synonyms:
                for ex in occupation.get("examples", []):
                    if query_lower in ex.lower() or ex.lower() in query_lower:
                        matched_synonyms.append(ex)
                        if len(matched_synonyms) >= 3:
                            break
            
            results.append({
                "nco_code": occupation["nco_code"],
                "title": occupation["title"],
                "description": occupation["description"],
                "score": float(score),
                "confidence": float(confidence),
                "matched_synonyms": matched_synonyms[:3]  # Limit to 3
            })
        
        return results
    
    def get_occupation(self, nco_code: str) -> Optional[Dict]:
        """Get occupation by nco_code."""
        for occ in self.occupations:
            if occ["nco_code"] == nco_code:
                return occ
        return None
