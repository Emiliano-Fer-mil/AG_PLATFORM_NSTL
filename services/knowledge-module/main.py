from fastapi import FastAPI, APIRouter
import psycopg2
import os
from pydantic import BaseModel
from typing import Literal, Optional


# -------------------
# APP
# -------------------

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


# -------------------
# HEALTH / DEBUG
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


# -------------------
# INGEST REQUEST MODEL
# -------------------

class IngestRequest(BaseModel):

    # knowledge.libraries
    library_name: str
    library_description: Optional[str] = None

    # knowledge.documents
    title: str
    content: str

    # knowledge.document_versions
    source_type: Literal["pdf", "md", "text", "html"]

    # metadata opcional
    description: Optional[str] = None

# -------------------
# ROUTE
# -------------------

@router.post("/ingest")
def ingest(payload: IngestRequest):
    service = IngestionService()
    return service.ingest(payload)


# IMPORTANTE: esto conecta el router
app.include_router(router)


# -------------------
# SERVICE LAYER
# -------------------

class IngestionService:

    def ingest(self, payload: IngestRequest):

        conn = get_conn()
        cur = conn.cursor()

        try:

            # ----------------------------------
            # 1. ENSURE LIBRARY EXISTS
            # ----------------------------------

            cur.execute("""
                SELECT id
                FROM knowledge.libraries
                WHERE name = %s
            """, (payload.library_name,))

            row = cur.fetchone()

            if row:
                library_id = row[0]
            else:
                cur.execute("""
                    INSERT INTO knowledge.libraries
                    (name, description)
                    VALUES (%s, %s)
                    RETURNING id
                """, (
                    payload.library_name,
                    payload.library_description
                ))

                library_id = cur.fetchone()[0]

            # ----------------------------------
            # 2. CREATE DOCUMENT
            # ----------------------------------

            cur.execute("""
                INSERT INTO knowledge.documents
                (library_id, title, content)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (
                library_id,
                payload.title,
                payload.content
            ))

            document_id = cur.fetchone()[0]

            # ----------------------------------
            # 3. CREATE DOCUMENT VERSION
            # ----------------------------------

            cur.execute("""
                INSERT INTO knowledge.document_versions
                (document_id, raw_text, source_type, status)
                VALUES (%s, %s, %s, 'active')
                RETURNING id
            """, (
                document_id,
                payload.content,
                payload.source_type
            ))

            version_id = cur.fetchone()[0]

            # ----------------------------------
            # 4. CHUNKING
            # ----------------------------------

            chunks = self._chunk(payload.content)

            for chunk in chunks:

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

                # ----------------------------------
                # 5. MOCK EMBEDDING
                # ----------------------------------

                embedding = [0.0] * 1536

                cur.execute("""
                    INSERT INTO knowledge.chunk_embeddings
                    (chunk_id, embedding, model)
                    VALUES (%s, %s::vector, %s)
                """, (
                    chunk_id,
                    embedding,
                    "mock-model"
                ))

            conn.commit()

            return {
                "status": "ok",
                "library_id": library_id,
                "document_id": document_id,
                "version_id": version_id,
                "chunks": len(chunks)
            }

        finally:
            conn.close()
    # -------------------
    # INTERNAL METHODS (DENTRO DE LA CLASE)
    # -------------------

    def _chunk(self, text: str):

        size = 500

        return [
            {
                "position": i,
                "content": text[i:i+size]
            }
            for i in range(0, len(text), size)
        ]
    
app.include_router(router)
