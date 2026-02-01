"""RAG helper module for searching the ChromaDB knowledge base."""

import os
from pathlib import Path

# Path to ChromaDB storage
CHROMA_DB_PATH = Path(__file__).parent / "chroma_db"

# OpenAI embedding model (fast API calls, no local model)
EMBEDDING_MODEL = "text-embedding-3-small"


def get_chroma_client():
    """Get or create ChromaDB client with persistent storage."""
    import chromadb
    return chromadb.PersistentClient(path=str(CHROMA_DB_PATH))


def get_embedding_function():
    """Get the embedding function for ChromaDB."""
    from chromadb.utils import embedding_functions
    api_key = os.getenv("OPENAI_API_KEY")
    # ChromaDB requires CHROMA_OPENAI_API_KEY env var
    if api_key and not os.getenv("CHROMA_OPENAI_API_KEY"):
        os.environ["CHROMA_OPENAI_API_KEY"] = api_key
    return embedding_functions.OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name=EMBEDDING_MODEL
    )


def get_collection():
    """Get the knowledge base collection."""
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    return client.get_or_create_collection(
        name="knowledge_base",
        embedding_function=embedding_fn
    )


def search(query: str, top_k: int = 10) -> list[str]:
    """
    Search the knowledge base for relevant information.
    
    Args:
        query: The search query string
        top_k: Number of results to return (default: 10)
    
    Returns:
        List of relevant text passages with source information
    """
    collection = get_collection()
    
    # Check if collection has any documents
    if collection.count() == 0:
        return ["The knowledge base is empty. Please run ingest.py to add documents."]
    
    # Perform similarity search with metadata
    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas"]
    )
    
    # Extract and return the documents with source info
    if results and results["documents"]:
        documents = results["documents"][0]  # First query's results
        metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(documents)
        
        # Format results with source attribution
        formatted_results = []
        for doc, meta in zip(documents, metadatas):
            source = meta.get("source", "Unknown source")
            # Clean up source name for readability
            source_name = source.replace(".txt", "").replace("_", " ")
            formatted_results.append(f"[Source: {source_name}]\n{doc}")
        
        return formatted_results if formatted_results else ["No relevant information found."]
    
    return ["No relevant information found."]


def get_document_count() -> int:
    """Get the number of documents in the knowledge base."""
    collection = get_collection()
    return collection.count()
