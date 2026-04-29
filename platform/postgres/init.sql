CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE SCHEMA IF NOT EXISTS knowledge;
CREATE SCHEMA IF NOT EXISTS assistants;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS system;

CREATE TABLE knowledge.libraries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE knowledge.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    library_id UUID REFERENCES knowledge.libraries(id) ON DELETE CASCADE,

    title TEXT,
    content TEXT NOT NULL,

    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE knowledge.document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES knowledge.documents(id) ON DELETE CASCADE,

    version INT NOT NULL DEFAULT 1,
    content_hash TEXT, -- detecta cambios

    raw_text TEXT NOT NULL,

    source_type TEXT CHECK (source_type IN ('pdf', 'md', 'text', 'html')),

    created_at TIMESTAMP DEFAULT now(),

    status TEXT CHECK (status IN ('active', 'deprecated')) DEFAULT 'active'
);

CREATE TABLE knowledge.chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    document_version_id UUID NOT NULL
        REFERENCES knowledge.document_versions(id)
        ON DELETE CASCADE,

    position INT NOT NULL, -- orden dentro del documento

    content TEXT NOT NULL,

    start_char INT,
    end_char INT,

    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE knowledge.chunk_embeddings (
    chunk_id UUID PRIMARY KEY
        REFERENCES knowledge.chunks(id)
        ON DELETE CASCADE,

    embedding vector(1536), -- ajustar al modelo real

    model TEXT NOT NULL, -- ej: text-embedding-3-small

    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX chunks_embedding_idx
ON knowledge.chunk_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX idx_chunks_version
ON knowledge.chunks(document_version_id, position);

CREATE INDEX idx_document_versions_doc
ON knowledge.document_versions(document_id, version);