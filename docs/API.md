# NCO Search API Documentation

Base URL: `http://localhost:8000`

## Endpoints

### Health Check
Check if the service is running and model is loaded.

**GET** `/health`

**Response:**
```json
{
  "status": "healthy",
  "model": "intfloat/multilingual-e5-small",
  "vectors_loaded": 13
}