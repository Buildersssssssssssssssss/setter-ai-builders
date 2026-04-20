import json
import os
from typing import List

import numpy as np
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from supabase import create_client, Client

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
EMBEDDING_MODEL = "text-embedding-3-small"
MATCH_COUNT = 3


def _supabase() -> Client:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    return create_client(url, key)


def _embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=EMBEDDING_MODEL)


# ── Ingestión ─────────────────────────────────────────────────────────────────

def ingest_file(file_path: str, source_name: str) -> int:
    """
    Carga un PDF o MD, lo trocea, genera embeddings y los guarda en Supabase.
    Borra los chunks anteriores del mismo source antes de insertar.
    Retorna el número de chunks insertados.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        documents = PyPDFLoader(file_path).load()
    elif ext in (".md", ".markdown", ".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        documents = [Document(page_content=text, metadata={"source": source_name})]
    else:
        raise ValueError(f"Formato no soportado: {ext}. Usa PDF, MD o TXT.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(documents)

    if not chunks:
        raise ValueError("El documento no produjo chunks. Verifica que el archivo tenga texto.")

    embeddings_model = _embeddings()
    texts = [chunk.page_content for chunk in chunks]
    embeddings = embeddings_model.embed_documents(texts)

    db = _supabase()

    # Elimina chunks anteriores del mismo source
    db.table("knowledge_chunks").delete().eq("source", source_name).execute()

    rows = [
        {"source": source_name, "content": text, "embedding": embedding}
        for text, embedding in zip(texts, embeddings)
    ]

    db.table("knowledge_chunks").insert(rows).execute()

    print(f"[RAG] Ingestión completa: source={source_name!r} chunks={len(rows)}")
    return len(rows)


# ── Búsqueda ──────────────────────────────────────────────────────────────────

def _cosine_similarity(a: List[float], b: List[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


def search_knowledge(query: str, match_count: int = MATCH_COUNT) -> List[str]:
    """
    Genera el embedding del query, trae todos los chunks de Supabase y retorna
    los más relevantes ordenados por similitud coseno calculada en Python.
    """
    query_embedding = _embeddings().embed_query(query)

    db = _supabase()
    result = db.table("knowledge_chunks").select("content, embedding").execute()

    if not result.data:
        print(f"[RAG] Sin chunks en la base de conocimiento")
        return []

    scored = []
    for row in result.data:
        raw = row.get("embedding")
        if not raw:
            continue
        vec = json.loads(raw) if isinstance(raw, str) else raw
        scored.append((row["content"], _cosine_similarity(query_embedding, vec)))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = [content for content, _ in scored[:match_count]]

    print(f"[RAG] {len(top)} chunks recuperados para query={query[:60]!r} "
          f"(top similarity={scored[0][1]:.3f} si hay resultados)" if scored else
          f"[RAG] Sin resultados para query={query!r}")
    return top
