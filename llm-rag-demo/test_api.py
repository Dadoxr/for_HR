"""Quick integration test - run against a live instance."""

import sys

import requests

BASE = "http://localhost:8001"


def test_health():
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    print(f"  Health: OK - providers: {[p['name'] for p in data['providers']]}")


def test_ingest():
    r = requests.post(
        f"{BASE}/ingest",
        json={
            "title": "Test Document",
            "text": "Python is a programming language. FastAPI is a web framework built on Python. "
            "PostgreSQL is a relational database that supports vector search via pgvector.",
            "source": "test",
        },
    )
    assert r.status_code == 200
    data = r.json()
    print(f"  Ingest: OK - doc_id={data['document_id']}, chunks={data['chunks_count']}")
    return data["document_id"]


def test_query(doc_id: str):
    r = requests.post(
        f"{BASE}/query",
        json={
            "question": "What is FastAPI?",
            "document_id": doc_id,
        },
    )
    if r.status_code == 503:
        print("  Query: SKIPPED - no LLM provider configured (expected without API keys)")
        return
    assert r.status_code == 200
    data = r.json()
    print(f"  Query: OK - confidence={data['confidence']}")


if __name__ == "__main__":
    print("Testing LLM RAG Demo API...")
    try:
        test_health()
        doc_id = test_ingest()
        test_query(doc_id)
        print("\nAll tests passed!")
    except Exception as e:
        print(f"\nFailed: {e}", file=sys.stderr)
        sys.exit(1)
