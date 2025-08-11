import os
import json
import time
import asyncio
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from collections import Counter, deque

from fastapi import FastAPI, HTTPException, Request, Query, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import orjson
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator

from inference import NCOEngine
from utils.logs import read_logs_reverse, parse_log_line
from security import SecurityHeadersMiddleware, RequestSizeLimitMiddleware
from translation_service import TranslationService, MultilingualSynonymBank
from voice_handler import VoiceHandler, VoiceInputRequest, VoiceInputResponse, get_voice_handler

# Load environment variables
load_dotenv()

# Configuration
EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small")
LOWCONF_SOFTMAX = float(os.getenv("LOWCONF_SOFTMAX", "0.55"))
LOWCONF_TOPSIM = float(os.getenv("LOWCONF_TOPSIM", "0.48"))
ENABLE_TRANSLATION = os.getenv("ENABLE_TRANSLATION", "false").lower() == "true"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
REINDEX_TIMEOUT_SEC = int(os.getenv("REINDEX_TIMEOUT_SEC", "300"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
DISABLE_UA_LOGGING = os.getenv("DISABLE_UA_LOGGING", "false").lower() == "true"
BUILD_TIME = os.getenv("BUILD_TIME", datetime.utcnow().isoformat())
GIT_SHA = os.getenv("GIT_SHA", "unknown")

# Global state
engine: Optional[NCOEngine] = None
translation_service: Optional[TranslationService] = None
synonym_bank: Optional[MultilingualSynonymBank] = None
voice_handler: Optional[VoiceHandler] = None
reindex_lock = asyncio.Lock()
is_reindexing = False
reindex_task: Optional[asyncio.Task] = None
app_version = "1.0.0"

# Ensure logs directory exists
logs_dir = Path(__file__).parent / "logs"
logs_dir.mkdir(exist_ok=True)

# Rate limiter: allow test-only header key when enabled
def rate_limit_key(request: Request) -> str:
    """Get rate limit key, allowing test override if enabled."""
    # Only honor test header if explicitly enabled
    if os.getenv("ALLOW_TEST_RATE_KEY", "false").lower() == "true":
        hdr = request.headers.get("x-rate-key")
        if hdr:
            return hdr
    return get_remote_address(request)

limiter = Limiter(key_func=rate_limit_key)

# Dynamic rate limits (evaluated per-request)
def rate_limit_search():
    """Get search rate limit from environment."""
    return os.getenv("RATE_LIMIT_SEARCH", "60/minute")

def rate_limit_admin():
    """Get admin rate limit from environment."""
    return os.getenv("RATE_LIMIT_ADMIN", "20/minute")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    k: int = Field(5, ge=1, le=20)
    language: Optional[str] = None


class SearchResult(BaseModel):
    nco_code: str
    title: str
    description: str
    score: float
    confidence: float
    matched_synonyms: List[str]


class SearchResponse(BaseModel):
    results: List[SearchResult]
    low_confidence: bool
    language: str
    translated: bool
    suggestions: Optional[List[str]] = None
    alternatives: Optional[List[str]] = None


class FeedbackRequest(BaseModel):
    query: str
    selected_code: Optional[str] = None
    results_helpful: bool
    comments: Optional[str] = None


class OccupationResponse(BaseModel):
    nco_code: str
    title: str
    description: str
    synonyms: List[str]
    examples: List[str]


class SynonymUpdate(BaseModel):
    nco_code: str
    add: Optional[List[str]] = None
    remove: Optional[List[str]] = None


class UpdateSynonymsRequest(BaseModel):
    updates: List[SynonymUpdate]


def require_admin(req: Request):
    """Require admin token if ADMIN_TOKEN is set. Accepts header or ?token= query."""
    if not ADMIN_TOKEN:
        return  # no-op in dev if not configured
    supplied = req.headers.get("x-admin-token") or req.query_params.get("token")
    if supplied != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global engine, translation_service, synonym_bank, voice_handler
    print(f"Loading NCO search engine with model: {EMBED_MODEL}")
    engine = NCOEngine(model_name=EMBED_MODEL, use_enhanced=True)
    print(f"Engine loaded with {engine.num_occupations} occupations")
    
    # Initialize translation service
    translation_service = TranslationService(use_online=False)
    print("Translation service initialized")
    
    # Initialize synonym bank
    synonym_bank = MultilingualSynonymBank()
    print("Synonym bank initialized")
    
    # Initialize voice handler
    try:
        voice_handler = get_voice_handler()
        print("Voice handler initialized")
    except Exception as e:
        print(f"Voice handler initialization failed: {e}")
        voice_handler = None
    
    yield
    # Shutdown
    engine = None
    translation_service = None
    synonym_bank = None
    voice_handler = None


app = FastAPI(
    title="NCO Semantic Search API",
    version=app_version,
    lifespan=lifespan
)

# Add rate limit error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_size=10_240)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics: always enable in dev/test
Instrumentator(
    excluded_handlers=["/metrics", "/health"],
    should_respect_env_var=False  # ensure /metrics is available
).instrument(app).expose(app, endpoint="/metrics")


def reload_engine():
    """Reload the NCO engine with updated data."""
    global engine
    try:
        new_engine = NCOEngine(model_name=EMBED_MODEL)
        engine = new_engine
        return True
    except Exception as e:
        print(f"Failed to reload engine: {e}")
        return False


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy" if not is_reindexing else "reindexing",
        "model": EMBED_MODEL,
        "vectors_loaded": engine.num_occupations if engine else 0,
        "version": app_version,
        "build_time": BUILD_TIME,
        "git_sha": GIT_SHA
    }


@app.post("/search", response_model=SearchResponse)
@limiter.limit(rate_limit_search)
async def search(search_request: SearchRequest, request: Request):
    """Search for occupations using semantic similarity."""
    if is_reindexing:
        raise HTTPException(status_code=503, detail="Service is reindexing, please try again in a moment")
    
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    # Start timing
    start_time = time.time()
    
    # Detect language if not provided
    detected_lang = engine.detect_language(search_request.query)
    language = search_request.language or detected_lang
    
    # Search
    results = engine.search(search_request.query, k=search_request.k)
    
    # Calculate latency
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Check for low confidence
    low_confidence = False
    top_result = None
    if results:
        top_result = results[0]
        top_score = top_result["score"]
        top_confidence = top_result["confidence"]
        low_confidence = top_score < LOWCONF_TOPSIM or top_confidence < LOWCONF_SOFTMAX
    else:
        low_confidence = True
    
    # Translation and enhancement for low confidence
    translated = False
    suggestions = None
    alternatives = None
    
    if low_confidence:
        # Get query enhancements
        enhanced = translation_service.enhance_low_confidence_query(search_request.query, language)
        suggestions = enhanced['suggestions']
        alternatives = enhanced['alternatives']
        
        # Try translation if enabled and not English
        if ENABLE_TRANSLATION and language != 'en':
            translated_query = translation_service.translate_query(search_request.query, language, 'en')
            if translated_query != search_request.query:
                # Search with translated query
                translated_results = engine.search(translated_query, k=search_request.k)
                if translated_results and translated_results[0]['score'] > top_score:
                    results = translated_results
                    translated = True
                    # Recalculate low confidence
                    top_result = results[0]
                    top_score = top_result["score"]
                    top_confidence = top_result["confidence"]
                    low_confidence = top_score < LOWCONF_TOPSIM or top_confidence < LOWCONF_SOFTMAX
    
    # Log search
    search_log = {
        "timestamp": datetime.utcnow().isoformat(),
        "query": search_request.query,
        "k": search_request.k,
        "language": language,
        "low_confidence": low_confidence,
        "top": {
            "nco_code": top_result["nco_code"] if top_result else None,
            "score": top_result["score"] if top_result else 0,
            "confidence": top_result["confidence"] if top_result else 0
        },
        "top_k": [r["nco_code"] for r in results],
        "model": EMBED_MODEL,
        "version": app_version,
        "latency_ms": latency_ms
    }
    
    # Append to search log
    search_file = logs_dir / "search.jsonl"
    with open(search_file, "ab") as f:
        f.write(orjson.dumps(search_log) + b"\n")
    
    # Format response
    search_results = [
        SearchResult(
            nco_code=r["nco_code"],
            title=r["title"],
            description=r["description"],
            score=r["score"],
            confidence=r["confidence"],
            matched_synonyms=r["matched_synonyms"]
        )
        for r in results
    ]
    
    return SearchResponse(
        results=search_results,
        low_confidence=low_confidence,
        language=language,
        translated=translated,
        suggestions=suggestions,
        alternatives=alternatives
    )


@app.get("/occupation/{nco_code}", response_model=OccupationResponse)
async def get_occupation(nco_code: str):
    """Get full details for an occupation code."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    occupation = engine.get_occupation(nco_code)
    if not occupation:
        raise HTTPException(status_code=404, detail=f"Occupation code {nco_code} not found")
    
    return OccupationResponse(**occupation)


@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest, req: Request):
    """Submit search feedback."""
    feedback_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "query": request.query,
        "selected_code": request.selected_code,
        "results_helpful": request.results_helpful,
        "comments": request.comments,
    }
    
    # Optionally include user agent
    if not DISABLE_UA_LOGGING:
        feedback_entry["user_agent"] = req.headers.get("user-agent")
    
    # Append to JSONL log
    feedback_file = logs_dir / "feedback.jsonl"
    with open(feedback_file, "ab") as f:
        f.write(orjson.dumps(feedback_entry) + b"\n")
    
    return {"status": "success"}


@app.post("/voice/transcribe", response_model=VoiceInputResponse)
@limiter.limit(rate_limit_search)
async def transcribe_voice(voice_request: VoiceInputRequest, request: Request):
    """Transcribe voice input to text."""
    if not voice_handler:
        raise HTTPException(
            status_code=501, 
            detail="Voice input not available. Install speech_recognition or whisper."
        )
    
    try:
        result = voice_handler.transcribe(
            voice_request.audio_data,
            voice_request.format,
            voice_request.language
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")


@app.post("/voice/search", response_model=SearchResponse)
@limiter.limit(rate_limit_search)
async def voice_search(voice_request: VoiceInputRequest, request: Request):
    """Transcribe voice input and search for occupations."""
    if not voice_handler:
        raise HTTPException(
            status_code=501,
            detail="Voice input not available. Install speech_recognition or whisper."
        )
    
    # Transcribe voice to text
    try:
        transcription = voice_handler.transcribe(
            voice_request.audio_data,
            voice_request.format,
            voice_request.language
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    
    # Create search request from transcription
    search_req = SearchRequest(
        query=transcription.text,
        k=5,
        language=transcription.language
    )
    
    # Perform search
    return await search(search_req, request)


@app.post("/voice/upload", response_model=VoiceInputResponse)
@limiter.limit(rate_limit_search)
async def upload_voice_file(
    file: UploadFile = File(...),
    language: Optional[str] = Query(None, description="Expected language (hi, bn, mr, en)"),
    request: Request = None
):
    """Upload and transcribe an audio file."""
    if not voice_handler:
        raise HTTPException(
            status_code=501,
            detail="Voice input not available. Install speech_recognition or whisper."
        )
    
    # Check file size (max 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")
    
    # Reset file pointer
    await file.seek(0)
    
    try:
        result = await voice_handler.process_audio_file(file, language)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")


@app.get("/admin/logs")
@limiter.limit(rate_limit_admin)
async def get_logs(
    request: Request,
    type: str = Query("search", enum=["search", "feedback", "audit"]),
    limit: int = Query(100, ge=1, le=1000),
    fields: Optional[str] = Query(None, enum=["basic", "full"]),
    _: None = Depends(require_admin)
):
    """Get recent logs."""
    log_file = logs_dir / f"{type}.jsonl"
    if not log_file.exists():
        return []
    
    logs = read_logs_reverse(log_file, limit)
    
    # Apply field filtering for basic view
    if fields == "basic" and type == "search":
        logs = [
            {
                "timestamp": log["timestamp"],
                "query": log["query"],
                "language": log["language"],
                "low_confidence": log["low_confidence"],
                "top_nco_code": log["top"]["nco_code"],
                "top_score": log["top"]["score"]
            }
            for log in logs
        ]
    
    return logs


@app.get("/admin/stats")
@limiter.limit(rate_limit_admin)
async def get_stats(request: Request = None, _: None = Depends(require_admin)):
    """Get aggregated statistics."""
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    
    # Read all search logs for stats
    search_file = logs_dir / "search.jsonl"
    feedback_file = logs_dir / "feedback.jsonl"
    
    all_searches = []
    searches_24h = []
    if search_file.exists():
        with open(search_file, "r") as f:
            for line in f:
                try:
                    log = orjson.loads(line)
                    all_searches.append(log)
                    log_time = datetime.fromisoformat(log["timestamp"].replace("Z", "+00:00"))
                    if log_time > last_24h:
                        searches_24h.append(log)
                except:
                    continue
    
    # Calculate search stats
    total_searches = len(all_searches)
    total_searches_24h = len(searches_24h)
    
    low_conf_count = sum(1 for s in all_searches if s["low_confidence"])
    low_conf_rate = low_conf_count / total_searches if total_searches > 0 else 0
    
    low_conf_count_24h = sum(1 for s in searches_24h if s["low_confidence"])
    low_conf_rate_24h = low_conf_count_24h / total_searches_24h if total_searches_24h > 0 else 0
    
    # Latency stats
    latencies = [s["latency_ms"] for s in all_searches if "latency_ms" in s]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    # Top queries and codes
    query_counter = Counter(s["query"].lower() for s in all_searches)
    code_counter = Counter(s["top"]["nco_code"] for s in all_searches if s["top"]["nco_code"])
    
    # Feedback stats
    helpful_count = 0
    total_feedback = 0
    if feedback_file.exists():
        with open(feedback_file, "r") as f:
            for line in f:
                try:
                    log = orjson.loads(line)
                    total_feedback += 1
                    if log["results_helpful"]:
                        helpful_count += 1
                except:
                    continue
    
    feedback_helpful_rate = helpful_count / total_feedback if total_feedback > 0 else 0
    
    return {
        "last_24h": {
            "total_searches": total_searches_24h,
            "low_confidence_rate": round(low_conf_rate_24h, 3),
        },
        "all_time": {
            "total_searches": total_searches,
            "low_confidence_rate": round(low_conf_rate, 3),
            "avg_latency_ms": round(avg_latency, 1),
            "feedback_helpful_rate": round(feedback_helpful_rate, 3),
            "top_queries": query_counter.most_common(10),
            "top_codes": code_counter.most_common(10)
        }
    }


@app.post("/admin/update-synonyms")
@limiter.limit(rate_limit_admin)
async def update_synonyms(request: UpdateSynonymsRequest, http_request: Request = None, _: None = Depends(require_admin)):
    """Update synonyms for occupations."""
    # Load current data
    data_file = Path(__file__).parent / "nco_data.json"
    sample_file = Path(__file__).parent / "nco_data.sample.json"
    
    # If no full data exists, copy sample
    if not data_file.exists() and sample_file.exists():
        import shutil
        shutil.copy(sample_file, data_file)
    
    if not data_file.exists():
        raise HTTPException(status_code=404, detail="No NCO data file found")
    
    with open(data_file, "r", encoding="utf-8") as f:
        occupations = json.load(f)
    
    # Create code lookup
    code_map = {occ["nco_code"]: occ for occ in occupations}
    
    # Apply updates
    updated_count = 0
    invalid_codes = []
    audit_changes = []
    
    for update in request.updates:
        if update.nco_code not in code_map:
            invalid_codes.append(update.nco_code)
            continue
        
        occ = code_map[update.nco_code]
        
        # Track changes for audit
        changes = {"nco_code": update.nco_code, "added": [], "removed": []}
        
        # Add synonyms
        if update.add:
            current_synonyms = set(occ.get("synonyms", []))
            new_synonyms = set(update.add) - current_synonyms
            if new_synonyms:
                current_synonyms.update(new_synonyms)
                occ["synonyms"] = list(current_synonyms)
                changes["added"] = list(new_synonyms)
                updated_count += 1
        
        # Remove synonyms
        if update.remove:
            current_synonyms = set(occ.get("synonyms", []))
            removed_synonyms = set(update.remove) & current_synonyms
            if removed_synonyms:
                for syn in removed_synonyms:
                    current_synonyms.discard(syn)
                occ["synonyms"] = list(current_synonyms)
                changes["removed"] = list(removed_synonyms)
                updated_count += 1
        
        if changes["added"] or changes["removed"]:
            audit_changes.append(changes)
    
    # Save updated data
    if updated_count > 0:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(occupations, f, ensure_ascii=False, indent=2)
        
        # Log audit trail
        audit_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": "update_synonyms",
            "user": http_request.headers.get("x-user-id", "admin"),
            "changes": audit_changes,
            "updated_count": updated_count
        }
        
        audit_file = logs_dir / "audit.jsonl"
        with open(audit_file, "ab") as f:
            f.write(orjson.dumps(audit_log) + b"\n")
    
    return {
        "ok": True,
        "updated": updated_count,
        "invalid_codes": invalid_codes,
        "requires_reindex": updated_count > 0,
        "changes": audit_changes
    }


@app.post("/admin/reindex")
@limiter.limit(rate_limit_admin)
async def reindex(request: Request = None, _: None = Depends(require_admin)):
    """Rebuild the FAISS index."""
    global is_reindexing

    async with reindex_lock:
        if is_reindexing:
            raise HTTPException(status_code=409, detail="Reindexing already in progress")

        is_reindexing = True
        start_time = time.time()

        try:
            # Resolve paths
            repo_root = Path(__file__).parent.parent  # nco-project/
            script_path = repo_root / "embeddings" / "build_index.py"

            # Use the current Python interpreter for venv correctness
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(repo_root)  # ensure build_index.py sees backend/ correctly
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=REINDEX_TIMEOUT_SEC
            )

            if proc.returncode != 0:
                raise Exception(f"Build failed: {stderr.decode(errors='ignore')}")

            # Reload engine
            if not reload_engine():
                raise Exception("Failed to reload engine")

            duration_ms = int((time.time() - start_time) * 1000)

            return {
                "ok": True,
                "duration_ms": duration_ms,
                "vectors": engine.num_occupations if engine else 0
            }

        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Reindexing timeout")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            is_reindexing = False


@app.delete("/admin/logs")
@limiter.limit(rate_limit_admin)
async def delete_logs(since: Optional[str] = None, request: Request = None, _: None = Depends(require_admin)):
    """Delete logs since a specific date."""
    if not since:
        return {
            "status": "error",
            "message": "Please provide 'since' parameter"
        }
    
    # Parse date
    try:
        since_date = datetime.fromisoformat(since.replace("Z", "+00:00"))
    except:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Filter and rewrite logs
    for log_type in ["search", "feedback"]:
        log_file = logs_dir / f"{log_type}.jsonl"
        if not log_file.exists():
            continue
        
        kept_logs = []
        with open(log_file, "r") as f:
            for line in f:
                try:
                    log = orjson.loads(line)
                    log_time = datetime.fromisoformat(log["timestamp"].replace("Z", "+00:00"))
                    if log_time < since_date:
                        kept_logs.append(line.strip())
                except:
                    continue
        
        # Rewrite file
        with open(log_file, "w") as f:
            for line in kept_logs:
                f.write(line + "\n")
    
    return {
        "status": "success",
        "message": f"Deleted logs since {since}"
    }


@app.delete("/admin/purge-logs")
@limiter.limit(rate_limit_admin)
async def purge_all_logs(request: Request = None, _: None = Depends(require_admin)):
    """Purge all logs."""
    for log_type in ["search", "feedback"]:
        log_file = logs_dir / f"{log_type}.jsonl"
        if log_file.exists():
            log_file.unlink()
    
    return {
        "status": "success", 
        "message": "All logs purged"
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)