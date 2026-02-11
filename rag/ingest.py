"""RAG document ingestion pipeline for ChromaDB."""

import logging
from pathlib import Path

from django.conf import settings

logger = logging.getLogger("rag")

DOCUMENTS_DIR = Path(__file__).resolve().parent / "documents"
COLLECTION_NAME = "kahrabaai_knowledge"


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 128) -> list[str]:
    """
    Split text into overlapping chunks by approximate word count.

    Args:
        text: The full document text.
        chunk_size: Approximate number of words per chunk.
        overlap: Number of words overlapping between consecutive chunks.

    Returns:
        List of text chunks.
    """
    words = text.split()
    if not words:
        return []

    if len(words) <= chunk_size:
        return [text]

    chunks = []
    step = chunk_size - overlap
    if step < 1:
        step = 1

    for i in range(0, len(words), step):
        chunk_words = words[i:i + chunk_size]
        chunks.append(" ".join(chunk_words))
        if i + chunk_size >= len(words):
            break

    return chunks


def _detect_language(filename: str) -> str:
    """Detect document language from filename convention."""
    if "_ar" in filename:
        return "ar"
    if "_en" in filename:
        return "en"
    return "both"


def ingest_all() -> int:
    """
    Ingest all .md files from rag/documents/ into ChromaDB.

    Uses intfloat/multilingual-e5-large for embeddings.
    ChromaDB PersistentClient at settings.CHROMA_PERSIST_DIR.
    Collection: "kahrabaai_knowledge" with cosine distance.

    Returns:
        Number of chunks ingested.

    Raises:
        ImportError: If chromadb or sentence_transformers not installed.
    """
    try:
        import chromadb
    except ImportError:
        raise ImportError(
            "chromadb is required for ingestion. "
            "Install with: pip install chromadb"
        )

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError(
            "sentence-transformers is required for ingestion. "
            "Install with: pip install sentence-transformers"
        )

    persist_dir = getattr(settings, "CHROMA_PERSIST_DIR", "./chroma_data")
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    logger.info("Loading embedding model intfloat/multilingual-e5-large...")
    model = SentenceTransformer("intfloat/multilingual-e5-large")

    total_chunks = 0

    if not DOCUMENTS_DIR.exists():
        logger.warning("Documents directory not found: %s", DOCUMENTS_DIR)
        return 0

    for md_file in sorted(DOCUMENTS_DIR.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        if not text.strip():
            continue

        chunks = chunk_text(text)
        language = _detect_language(md_file.name)

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            doc_id = f"{md_file.stem}_{i}"
            embedding = model.encode(f"passage: {chunk}").tolist()

            ids.append(doc_id)
            embeddings.append(embedding)
            documents.append(chunk)
            metadatas.append({
                "source": md_file.name,
                "language": language,
                "chunk_index": i,
            })

        if ids:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            total_chunks += len(ids)
            logger.info("Ingested %s: %d chunks", md_file.name, len(ids))

    logger.info("Total chunks ingested: %d", total_chunks)
    return total_chunks
