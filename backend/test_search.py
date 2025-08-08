import json
from pathlib import Path
from fastapi.testclient import TestClient
import sys
sys.path.append(str(Path(__file__).parent.parent))

from main import app

client = TestClient(app)


def test_health():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "model" in data
    assert "vectors_loaded" in data


def test_search_english():
    """Test English search."""
    response = client.post("/search", json={
        "query": "welding",
        "k": 5
    })
    assert response.status_code == 200
    data = response.json()
    
    assert "results" in data
    assert len(data["results"]) > 0
    assert "low_confidence" in data
    assert data["language"] == "en"
    assert data["translated"] is False
    
    # Check result structure
    result = data["results"][0]
    assert all(key in result for key in ["code", "title", "description", "score", "confidence", "matched_synonyms"])


def test_search_hindi():
    """Test Hindi search."""
    response = client.post("/search", json={
        "query": "वेल्डिंग",
        "k": 3
    })
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["results"]) <= 3
    assert data["language"] == "hi"


def test_get_occupation():
    """Test occupation detail endpoint."""
    # First search to get a valid code
    search_response = client.post("/search", json={
        "query": "welder",
        "k": 1
    })
    code = search_response.json()["results"][0]["code"]
    
    # Get occupation details
    response = client.get(f"/occupation/{code}")
    assert response.status_code == 200
    data = response.json()
    
    assert data["code"] == code
    assert all(key in data for key in ["title", "description", "synonyms", "examples"])


def test_get_occupation_not_found():
    """Test occupation not found."""
    response = client.get("/occupation/9999.9999")
    assert response.status_code == 404


def test_feedback():
    """Test feedback submission."""
    response = client.post("/feedback", json={
        "query": "test query",
        "selected_code": "7212.0100",
        "results_helpful": True,
        "comments": "Good results"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_search_low_confidence():
    """Test low confidence detection."""
    response = client.post("/search", json={
        "query": "quantum physics research",  # Unlikely occupation
        "k": 5
    })
    assert response.status_code == 200
    data = response.json()
    
    # Should have low confidence for out-of-domain query
    assert data["low_confidence"] is True


def test_admin_logs():
    """Test admin log endpoints."""
    # Test delete with since parameter
    response = client.delete("/admin/logs?since=2025-01-01")
    assert response.status_code == 200
    
    # Test purge all
    response = client.delete("/admin/purge-logs")
    assert response.status_code == 200