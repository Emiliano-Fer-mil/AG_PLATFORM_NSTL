from fastapi import FastAPI
from fastapi import APIRouter
import psycopg2
import os
from pydantic import BaseModel
from typing import Literal, Optional

app = FastAPI()
router = APIRouter()

# -------------------
# DB CONNECTION
# -------------------

def get_conn():
    return psycopg2.connect(
        host="platform-postgres",
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        port=int(os.getenv("POSTGRES_PORT", 5432))
    )

#SMOKE TEST INFRA
# -------------------
# HEALTH
# -------------------

@app.get("/health")
def health():
    return {"status": "ok", "service": "knowledge-module"}

@app.get("/db-test")
def db_test():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    result = cur.fetchone()
    conn.close()

    return {"db": "ok", "result": result}

# END SMOKE TEST INFRA

# -------------------
# DOCUMENT INGESTION (MVP STARTS HERE)
# -------------------

class IngestRequest(BaseModel):
    library_id: str
    source_type: Literal["text"]
    content: str
    title: Optional[str] = None
    source: Optional[str] = None


@router.post("/ingest")
def ingest(payload: IngestRequest):
    service = IngestionService()
    return service.ingest(payload)

class IngestionService:

    def ingest(self, payload: IngestRequest):

        text = payload.content

        version_id = self._create_version(payload)

        chunks = self._chunk(text)

        self._store(version_id, chunks)

        return {
            "status": "ok",
            "version_id": version_id,
            "chunks": len(chunks)
        }
    
def _create_version(self, payload):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO knowledge.document_versions
        (document_id, raw_text, source_type, status)
        VALUES (%s, %s, %s, 'active')
        RETURNING id
    """, (
        payload.library_id,
        payload.content,
        payload.source_type
    ))

    version_id = cur.fetchone()[0]

    conn.commit()
    conn.close()

    return version_id

def _chunk(self, text: str):

    size = 500

    return [
        {
            "position": i,
            "content": text[i:i+size]
        }
        for i in range(0, len(text), size)
    ]

def _store(self, version_id, chunks):

    conn = get_conn()
    cur = conn.cursor()

    for chunk in chunks:

        # 1. insert chunk
        cur.execute("""
            INSERT INTO knowledge.chunks
            (document_version_id, position, content)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (
            version_id,
            chunk["position"],
            chunk["content"]
        ))

        chunk_id = cur.fetchone()[0]

        # 2. embedding (placeholder)
        embedding = [0.0] * 1536

        cur.execute("""
            INSERT INTO knowledge.chunk_embeddings
            (chunk_id, embedding, model)
            VALUES (%s, %s, %s)
        """, (
            chunk_id,
            embedding,
            "mock-model"
        ))

    conn.commit()
    conn.close()
