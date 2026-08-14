from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


# ==========================================
# CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
CHROMA_DIR = BASE_DIR / "chroma_db"

COLLECTION_NAME = "zepto_policies"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


# ==========================================
# LOAD DOCUMENTS
# ==========================================

def load_documents():
    documents = []

    for file_path in sorted(DOCS_DIR.glob("doc_*.txt")):
        text = file_path.read_text(
            encoding="utf-8"
        ).strip()

        if not text:
            continue

        documents.append(
            {
                "id": file_path.stem,
                "text": text,
            }
        )

    return documents


# ==========================================
# CHUNK DOCUMENTS
# ==========================================

def chunk_documents(documents):
    """
    The supplied policy documents are short enough
    that one chunk per document is appropriate.
    """

    chunks = []

    for document in documents:
        chunks.append(
            {
                "id": document["id"] + "_chunk_0",
                "document_id": document["id"],
                "text": document["text"],
            }
        )

    return chunks


# ==========================================
# CREATE CHROMADB COLLECTION
# ==========================================

def create_collection():
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "description": "Zepto support policy corpus"
        },
    )

    return collection


# ==========================================
# INGEST DOCUMENTS
# ==========================================

def ingest():
    print("=" * 60)
    print("ZEPTO POLICY INGESTION")
    print("=" * 60)

    documents = load_documents()

    print(f"Documents loaded: {len(documents)}")

    if len(documents) != 8:
        raise ValueError(
            f"Expected 8 documents, found {len(documents)}"
        )

    chunks = chunk_documents(documents)

    print(f"Chunks created: {len(chunks)}")

    print(
        f"\nLoading embedding model: "
        f"{EMBEDDING_MODEL}"
    )

    model = SentenceTransformer(
        EMBEDDING_MODEL
    )

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    print("\nGenerating embeddings...")

    embeddings = model.encode(
        texts,
        normalize_embeddings=True
    )

    print(
        "Embedding shape:",
        embeddings.shape
    )

    collection = create_collection()

    collection.upsert(
        ids=[
            chunk["id"]
            for chunk in chunks
        ],
        documents=texts,
        embeddings=embeddings.tolist(),
        metadatas=[
            {
                "document_id": chunk["document_id"],
                "chunk_id": chunk["id"],
            }
            for chunk in chunks
        ],
    )

    print("\nChromaDB collection:")
    print(f"  Name: {COLLECTION_NAME}")
    print(f"  Stored chunks: {collection.count()}")

    print("\nIngestion completed successfully.")


if __name__ == "__main__":
    ingest()