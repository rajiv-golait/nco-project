import sys
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

@pytest.fixture(scope="session")
def ensure_index_built():
    """Ensure FAISS index is built before running tests."""
    index_path = Path(__file__).parent.parent / "faiss_index" / "nco.index"
    
    if not index_path.exists():
        print("Building FAISS index for tests...")
        embeddings_script = Path(__file__).parent.parent.parent / "embeddings" / "build_index.py"
        result = subprocess.run([sys.executable, str(embeddings_script)], 
                              cwd=Path(__file__).parent.parent.parent,
                              capture_output=True, text=True)
        if result.returncode != 0:
            pytest.fail(f"Failed to build index: {result.stderr}")
        print("Index built successfully")

@pytest.fixture
def client(ensure_index_built):
    """Create test client with index pre-built."""
    from main import app
    return TestClient(app)