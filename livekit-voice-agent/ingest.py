"""Data ingestion script for loading files into ChromaDB."""

import os
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
import rag

# Supported file extensions
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".py", ".json", ".csv"}

# Path to data directory
DATA_DIR = Path(__file__).parent / "data"


def read_file(file_path: Path) -> str:
    """Read content from a file."""
    suffix = file_path.suffix.lower()
    
    if suffix == ".pdf":
        return read_pdf(file_path)
    else:
        # Text-based files
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as f:
                return f.read()


def read_pdf(file_path: Path) -> str:
    """Read content from a PDF file."""
    try:
        # Try using pypdf if available
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except ImportError:
        print(f"Warning: pypdf not installed. Skipping PDF file: {file_path}")
        return ""


def get_files_to_process() -> list[Path]:
    """Get all supported files from the data directory."""
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True)
        return []
    
    files = []
    for file_path in DATA_DIR.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(file_path)
    
    return files


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 200) -> list[str]:
    """Split text into chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    return splitter.split_text(text)


def ingest_files():
    """Main function to ingest all files into ChromaDB."""
    files = get_files_to_process()
    
    if not files:
        print(f"No files found in {DATA_DIR}")
        print(f"Supported extensions: {', '.join(SUPPORTED_EXTENSIONS)}")
        print("\nPlease add your files to the data/ directory and run this script again.")
        return
    
    print(f"Found {len(files)} file(s) to process:")
    for f in files:
        print(f"  - {f.name}")
    print()
    
    # Get the ChromaDB collection
    collection = rag.get_collection()
    
    # Clear existing data
    existing_count = collection.count()
    if existing_count > 0:
        print(f"Clearing {existing_count} existing documents...")
        # Get all IDs and delete them
        all_ids = collection.get()["ids"]
        if all_ids:
            collection.delete(ids=all_ids)
    
    all_chunks = []
    all_ids = []
    all_metadatas = []
    
    for file_path in files:
        print(f"Processing: {file_path.name}...")
        
        # Read file content
        content = read_file(file_path)
        if not content.strip():
            print(f"  Skipping empty file: {file_path.name}")
            continue
        
        # Chunk the content
        chunks = chunk_text(content)
        print(f"  Created {len(chunks)} chunks")
        
        # Add to batch
        for i, chunk in enumerate(chunks):
            chunk_id = f"{file_path.stem}_{i}"
            all_chunks.append(chunk)
            all_ids.append(chunk_id)
            all_metadatas.append({
                "source": file_path.name,
                "chunk_index": i,
                "total_chunks": len(chunks)
            })
    
    if all_chunks:
        print(f"\nAdding {len(all_chunks)} chunks to ChromaDB...")
        
        # Add in batches to avoid memory issues
        batch_size = 100
        for i in range(0, len(all_chunks), batch_size):
            batch_end = min(i + batch_size, len(all_chunks))
            collection.add(
                documents=all_chunks[i:batch_end],
                ids=all_ids[i:batch_end],
                metadatas=all_metadatas[i:batch_end]
            )
        
        print(f"Successfully indexed {len(all_chunks)} chunks!")
        print(f"\nTotal documents in knowledge base: {collection.count()}")
    else:
        print("No content was extracted from the files.")


if __name__ == "__main__":
    ingest_files()
