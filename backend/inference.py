import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
import faiss
from sentence_transformers import SentenceTransformer
import langdetect
import sqlite3
from datetime import datetime
import hashlib
from langdetect import DetectorFactory

# Make language detection deterministic
DetectorFactory.seed = 42


class AuditSystem:
    """Lightweight audit logger integrated in the same file to avoid new files."""
    DB_PATH = Path("data/audit_trail.db")

    def __init__(self):
        # Ensure parent directory exists
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS search_audit (
                id TEXT PRIMARY KEY,
                timestamp DATETIME,
                query TEXT,
                results_count INTEGER,
                top_result_code TEXT,
                top_result_conf REAL
            )
        """)
        conn.commit()
        conn.close()

    def get_analytics(self, days: int = 7) -> Dict[str, float]:
        """Return simple stats for last N days."""
        import datetime as _dt
        since = _dt.datetime.utcnow() - _dt.timedelta(days=days)
        conn = sqlite3.connect(self.DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), AVG(top_result_conf) FROM search_audit WHERE timestamp > ?", (since,))
        total, avg_conf = cur.fetchone()
        conn.close()
        return {"total_searches": total or 0, "avg_confidence": round(avg_conf or 0.0, 3)}

    def log_search(self, query: str, results: List[Dict]):
        audit_id = hashlib.md5(f"{query}{datetime.utcnow()}".encode()).hexdigest()
        top_code = results[0]["nco_code"] if results else None
        top_conf = results[0]["confidence"] if results else None
        conn = sqlite3.connect(self.DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO search_audit VALUES (?,?,?,?,?,?)",
            (audit_id, datetime.utcnow(), query, len(results), top_code, top_conf)
        )
        conn.commit()
        conn.close()


class NCOEngine:
    # Synonym bank can later be externalized; kept inline to avoid creating new files
    SYNONYM_BANK = {
        "tailor": ["sewing machine operator", "garment maker", "seamstress"],
        "driver": ["vehicle operator", "chauffeur", "transport operator"],
        "teacher": ["educator", "instructor", "tutor", "faculty"],
        "it professional": ["software developer", "programmer", "coder"],
        "healthcare worker": ["medical professional", "health practitioner"],
        "coolie": ["porter", "loader", "cargo handler"],
        "mali": ["gardener", "horticulturist", "landscaper"],
    }

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small", use_enhanced: bool = True):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.use_enhanced = use_enhanced
        
        # Try to load enhanced data first if available
        if use_enhanced:
            enhanced_data_file = Path("nco_data_enhanced.json")
            if enhanced_data_file.exists():
                with open(enhanced_data_file, "r", encoding="utf-8") as f:
                    self.occupations = json.load(f)
                print(f"Loaded enhanced NCO data with {len(self.occupations)} occupations")
                # Create code lookup for quick access
                self.code_lookup = {occ["nco_code"]: occ for occ in self.occupations}
        
        # Load FAISS index and metadata
        index_dir = Path("faiss_index")
        if not index_dir.exists():
            raise RuntimeError("FAISS index not found. Run embeddings/build_index.py first.")
        
        self.index = faiss.read_index(str(index_dir / "nco.index"))
        
        with open(index_dir / "meta.json", "r", encoding="utf-8") as f:
            self.metadata = json.load(f)
        
        # Use metadata occupations if enhanced not loaded
        if not hasattr(self, 'occupations'):
            self.occupations = self.metadata["occupations"]
            self.code_lookup = {occ["nco_code"]: occ for occ in self.occupations}
        
self.num_occupations = len(self.occupations)

        # Build auxiliary indexes for fallback strategies
        self._build_aux_indexes()

        # Init lightweight audit system
        self.audit = AuditSystem()
    
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
    
    def _build_aux_indexes(self):
        """Create simple in-memory indexes for quick keyword and fuzzy fallback."""
        from collections import defaultdict
        self.title_index: Dict[str, Dict] = {}
        self.keyword_index: Dict[str, List[Dict]] = defaultdict(list)
        for occ in self.occupations:
            title_lc = occ["title"].lower()
            self.title_index[title_lc] = occ
            for word in title_lc.split():
                self.keyword_index[word].append(occ)
            for syn in occ.get("synonyms", []):
                for word in syn.lower().split():
                    self.keyword_index[word].append(occ)

    def _expand_query_with_synonyms(self, query: str) -> List[str]:
        """Generate synonym-expanded queries."""
        variants = [query]
        lower_q = query.lower()
        for term, syns in self.SYNONYM_BANK.items():
            if term in lower_q:
                for s in syns:
                    variants.append(lower_q.replace(term, s))
        return list(set(variants))

    def _fuzzy_fallback(self, query: str) -> List[Dict]:
        """Use difflib to find close title matches."""
        import difflib
        titles = list(self.title_index.keys())
        close = difflib.get_close_matches(query.lower(), titles, n=5, cutoff=0.6)
        results = []
        for t in close:
            occ = self.title_index[t]
            results.append({
                "nco_code": occ["nco_code"],
                "title": occ["title"],
                "description": occ["description"],
                "score": 0.0,
                "confidence": 0.2,
                "matched_synonyms": [],
                "hierarchy": occ.get("hierarchy"),
                "breadcrumb": occ.get("breadcrumb"),
            })
        return results

    def _keyword_fallback(self, query: str) -> List[Dict]:
        """Return occupations that share any keyword with the query, ranked by overlap."""
        words = [w.lower() for w in query.split() if len(w) > 2]
        scores = {}
        for w in words:
            for occ in self.keyword_index.get(w, []):
                code = occ["nco_code"]
                scores.setdefault(code, 0)
                scores[code] += 1
        # Rank by score desc
        ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:10]
        results = []
        for code, sc in ranked:
            occ = self.code_lookup[code]
            results.append({
                "nco_code": code,
                "title": occ["title"],
                "description": occ["description"],
                "score": float(sc),
                "confidence": 0.25,  # heuristic low confidence
                "matched_synonyms": [],
                "hierarchy": occ.get("hierarchy"),
                "breadcrumb": occ.get("breadcrumb"),
            })
        return results

    def search(self, query: str, k: int = 5, division_filter: str = None, minor_group_filter: str = None) -> List[Dict]:
        """Search for similar occupations."""
        # Support synonym expansion fallback if first attempt is low confidence
        candidate_queries = [query]
        results: List[Dict] = []

        for attempt, q in enumerate(candidate_queries + self._expand_query_with_synonyms(query)):
            # Avoid redundant queries
            if q in candidate_queries and attempt != 0:
                continue
            query_embedding = self.embed_query(q)
            distances, indices = self.index.search(
                query_embedding.reshape(1, -1),
                min(k * 3, self.num_occupations)  # fetch more for filtering and scoring
            )

            temp_results = []
            scores = distances[0]
            exp_scores = np.exp(scores - np.max(scores))
            softmax_scores = exp_scores / np.sum(exp_scores) if np.sum(exp_scores) else scores

            for idx_faiss, (faiss_idx, score, conf) in enumerate(zip(indices[0], scores, softmax_scores)):
                if faiss_idx == -1:
                    continue
                occupation = self.occupations[faiss_idx]

                # Hierarchy filter
                if division_filter and occupation.get("hierarchy", {}).get("division_code") != division_filter:
                    continue
                if minor_group_filter and occupation.get("hierarchy", {}).get("minor_group_code") != minor_group_filter:
                    continue

                result = {
                    "nco_code": occupation["nco_code"],
                    "title": occupation["title"],
                    "description": occupation["description"],
                    "score": float(score),
                    "confidence": float(conf),
                    "matched_synonyms": [],
                }
                if "hierarchy" in occupation:
                    result["hierarchy"] = occupation["hierarchy"]
                if "breadcrumb" in occupation:
                    result["breadcrumb"] = occupation["breadcrumb"]

                temp_results.append(result)

                if len(temp_results) >= k:
                    break

            # If we gathered enough high-confidence results, stop fallback loop
            if temp_results and temp_results[0]["confidence"] >= 0.5:
                results = temp_results[:k]
                break
            # else continue to next variant
            if not results:
                results = temp_results[:k]

        # If still low-confidence results (<0.3) trigger keyword/fuzzy fallback
        if not results or results[0]["confidence"] < 0.3:
            keyword_fallback = self._keyword_fallback(query) + self._fuzzy_fallback(query)
            # Merge ensuring uniqueness
            results_codes = {r["nco_code"] for r in results}
            for r in keyword_fallback:
                if r["nco_code"] not in results_codes and len(results) < k:
                    results.append(r)
                    results_codes.add(r["nco_code"])

        # Compute matched_synonyms for final results
        query_lower = query.lower()
        for res in results:
            occ = self.code_lookup[res["nco_code"]]
            matches = []
            if query_lower in occ["title"].lower():
                matches.append(occ["title"])
            for syn in occ.get("synonyms", []):
                if query_lower in syn.lower() or syn.lower() in query_lower:
                    matches.append(syn)
            res["matched_synonyms"] = matches[:3]

        # Audit logging (non-blocking best-effort)
        try:
            self.audit.log_search(query, results)
        except Exception:
            pass

        return results
        
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
            
            # Include hierarchy if available
            result = {
                "nco_code": occupation["nco_code"],
                "title": occupation["title"],
                "description": occupation["description"],
                "score": float(score),
                "confidence": float(confidence),
                "matched_synonyms": matched_synonyms[:3]  # Limit to 3
            }
            
            # Add hierarchy info if available
            if "hierarchy" in occupation:
                result["hierarchy"] = occupation["hierarchy"]
            if "breadcrumb" in occupation:
                result["breadcrumb"] = occupation["breadcrumb"]
            
            results.append(result)
        
        return results
    
    def get_occupation(self, nco_code: str) -> Optional[Dict]:
        """Get occupation by nco_code."""
        # Use lookup if available for O(1) access
        if hasattr(self, 'code_lookup'):
            return self.code_lookup.get(nco_code)
        
        # Fallback to linear search
        for occ in self.occupations:
            if occ["nco_code"] == nco_code:
                return occ
        return None
    
    def search_by_hierarchy(self, division: Optional[str] = None, 
                           sub_division: Optional[str] = None,
                           minor_group: Optional[str] = None) -> List[Dict]:
        """Search occupations by hierarchical classification."""
        results = []
        
        for occ in self.occupations:
            if "hierarchy" not in occ:
                continue
            
            hierarchy = occ["hierarchy"]
            
            # Check division match
            if division and hierarchy.get("division_code") != division:
                continue
            
            # Check sub-division match
            if sub_division and hierarchy.get("sub_division_code") != sub_division:
                continue
            
            # Check minor group match
            if minor_group and hierarchy.get("minor_group_code") != minor_group:
                continue
            
            results.append(occ)
        
        return results
