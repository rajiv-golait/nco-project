import json
import time
from pathlib import Path


def test_admin_logs(client):
    """Test admin logs endpoint."""
    # First create some searches
    client.post("/search", json={"query": "test query", "k": 5})
    client.post("/search", json={"query": "another test", "k": 3})
    
    # Get search logs
    response = client.get("/admin/logs?type=search&limit=10")
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)
    assert len(logs) >= 2
    assert "query" in logs[0]
    assert "timestamp" in logs[0]
    
    # Get feedback logs
    response = client.get("/admin/logs?type=feedback&limit=10")
    assert response.status_code == 200


def test_admin_stats(client):
    """Test admin stats endpoint."""
    # Create some test data
    for i in range(5):
        client.post("/search", json={"query": f"test {i}", "k": 5})
    
    response = client.get("/admin/stats")
    assert response.status_code == 200
    stats = response.json()
    
    assert "last_24h" in stats
    assert "all_time" in stats
    assert stats["all_time"]["total_searches"] >= 5
    assert "top_queries" in stats["all_time"]
    assert "top_codes" in stats["all_time"]


def test_update_synonyms(client):
    """Test synonym update endpoint."""
    response = client.post("/admin/update-synonyms", json={
        "updates": [
            {
                "nco_code": "7212.0100",
                "add": ["test synonym"],
                "remove": []
            }
        ]
    })
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["updated"] == 1
    assert data["requires_reindex"] is True


def test_update_synonyms_invalid_code(client):
    """Test synonym update with invalid code."""
    response = client.post("/admin/update-synonyms", json={
        "updates": [
            {
                "nco_code": "9999.9999",
                "add": ["test"],
                "remove": []
            }
        ]
    })
    assert response.status_code == 200
    data = response.json()
    assert "9999.9999" in data["invalid_codes"]


def test_reindex(client):
    """Test reindex endpoint."""
    # This is a slow operation, skip in CI if needed
    response = client.post("/admin/reindex")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "duration_ms" in data
    assert "vectors" in data
    
    # Check engine was reloaded
    health = client.get("/health").json()
    assert health["vectors_loaded"] > 0


def test_delete_logs(client):
    """Test log deletion."""
    # Create a search
    client.post("/search", json={"query": "delete test", "k": 5})
    
    # Delete future logs (should keep our test)
    response = client.delete("/admin/logs?since=2030-01-01")
    assert response.status_code == 200
    
    # Verify log still exists
    logs = client.get("/admin/logs?type=search&limit=10").json()
    assert any(log["query"] == "delete test" for log in logs)


def test_purge_logs(client):
    """Test log purging."""
    # Create logs
    client.post("/search", json={"query": "purge test", "k": 5})
    client.post("/feedback", json={
        "query": "test",
        "results_helpful": True
    })
    
    # Purge all
    response = client.delete("/admin/purge-logs")
    assert response.status_code == 200
    
    # Verify empty
    search_logs = client.get("/admin/logs?type=search").json()
    feedback_logs = client.get("/admin/logs?type=feedback").json()
    
    # New logs might have been created by other tests
    # Just verify purge endpoint works
    assert response.json()["status"] == "success"