"""Data ingestion script for loading files into ChromaDB."""

import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
import rag

# Load environment variables
env_path_local = Path(__file__).resolve().parent / ".env.local"
env_path_parent = Path(__file__).resolve().parent.parent / ".env.local"
load_dotenv(env_path_local)
load_dotenv(env_path_parent)

# Only process txt files (podcast transcripts)
SUPPORTED_EXTENSIONS = {".txt"}

# Path to data directory
DATA_DIR = Path(__file__).parent / "data"
SEQUOIA_JSON = DATA_DIR / "sequoia_data.json"


def clean_transcript(text: str) -> str:
    """Clean transcript text by removing timestamps and normalizing whitespace."""
    # Remove timestamp patterns like "00:01", "01:23:45", etc.
    text = re.sub(r'\d{1,2}:\d{2}(?::\d{2})?\s*\n?\s*', '', text)
    
    # Remove duplicate newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove standalone [Music] or [Applause] markers
    text = re.sub(r'\[Music\]|\[Applause\]|\[Laughter\]', '', text, flags=re.IGNORECASE)
    
    return text.strip()


def clean_markdown(text: str) -> str:
    """Clean markdown content from Sequoia website."""
    # Remove navigation links at the start
    text = re.sub(r'^\[Skip to main content\].*?\n', '', text)
    text = re.sub(r'^\[\s*\]\(https://sequoiacap\.com[^)]*\)', '', text)
    
    # Remove navigation menu items
    lines = text.split('\n')
    clean_lines = []
    skip_nav = True
    for line in lines:
        # Skip navigation-like lines at the start
        if skip_nav and re.match(r'^\s*\*\s*\[', line):
            continue
        if skip_nav and 'Open search' in line:
            skip_nav = False
            continue
        skip_nav = False
        clean_lines.append(line)
    
    text = '\n'.join(clean_lines)
    
    # Remove image links
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    
    # Remove duplicate newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def extract_sequoia_articles():
    """Extract meaningful article content from sequoia_data.json."""
    if not SEQUOIA_JSON.exists():
        return []
    
    print(f"Loading {SEQUOIA_JSON.name}...")
    with open(SEQUOIA_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    pages = data.get('pages', [])
    print(f"  Found {len(pages)} pages")
    
    articles = []
    # Skip patterns for non-content pages
    skip_patterns = [
        r'/our-team/', r'/our-companies/', r'/legal', r'/privacy',
        r'/cookie', r'/careers', r'/contact', r'/tag/', r'/page/',
    ]
    
    for page in pages:
        url = page.get('url', '')
        title = page.get('title', '')
        markdown = page.get('markdown', '')
        
        # Skip non-content pages
        if any(re.search(p, url, re.I) for p in skip_patterns):
            continue
        
        # Skip short content (likely navigation pages)
        if not markdown or len(markdown) < 500:
            continue
        
        # Clean the markdown
        clean_md = clean_markdown(markdown)
        if len(clean_md) < 300:
            continue
        
        # Extract title for source
        source = title.replace(' | Sequoia Capital', '').replace(' | Sequoia', '').strip()
        if not source:
            source = 'Sequoia Article'
        
        articles.append({
            'content': clean_md,
            'source': source
        })
    
    print(f"  Extracted {len(articles)} content-rich articles")
    return articles


def read_file(file_path: Path) -> str:
    """Read content from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as f:
            content = f.read()
    
    return clean_transcript(content)


def get_files_to_process() -> list[Path]:
    """Get all supported files from the data directory."""
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True)
        return []
    
    files = []
    for file_path in DATA_DIR.rglob("*"):
        if file_path.is_file():
            if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(file_path)
    
    return files


def chunk_text(text: str, source_name: str, chunk_size: int = 2000, chunk_overlap: int = 400) -> list[str]:
    """Split text into larger, more contextual chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_text(text)
    
    # Prepend source info to each chunk for better context
    return [f"[From: {source_name}]\n{chunk}" for chunk in chunks]


def ingest_files():
    """Main function to ingest all files into ChromaDB."""
    # Get transcript files
    files = get_files_to_process()
    print(f"Found {len(files)} transcript file(s)")
    
    # Get Sequoia website articles
    sequoia_articles = extract_sequoia_articles()
    
    # Get the ChromaDB collection
    collection = rag.get_collection()
    
    # Clear existing data
    existing_count = collection.count()
    if existing_count > 0:
        print(f"\nClearing {existing_count} existing documents...")
        all_ids = collection.get()["ids"]
        if all_ids:
            collection.delete(ids=all_ids)
    
    all_chunks = []
    all_ids = []
    all_metadatas = []
    
    # Process transcript files
    print(f"\nProcessing transcript files...")
    for file_path in files:
        content = read_file(file_path)
        if not content.strip():
            continue
        
        source_name = file_path.stem.replace("_", " ")
        chunks = chunk_text(content, source_name)
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"transcript_{file_path.stem}_{i}"
            all_chunks.append(chunk)
            all_ids.append(chunk_id)
            all_metadatas.append({
                "source": source_name,
                "type": "transcript",
                "chunk_index": i
            })
    
    print(f"  Created {len(all_chunks)} chunks from transcripts")
    
    # Process Sequoia articles
    print(f"\nProcessing Sequoia website articles...")
    article_chunks = 0
    for idx, article in enumerate(sequoia_articles):
        chunks = chunk_text(article['content'], article['source'])
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"sequoia_{idx}_{i}"
            all_chunks.append(chunk)
            all_ids.append(chunk_id)
            all_metadatas.append({
                "source": article['source'],
                "type": "website",
                "chunk_index": i
            })
        article_chunks += len(chunks)
    
    print(f"  Created {article_chunks} chunks from Sequoia articles")
    
    if all_chunks:
        print(f"\nAdding {len(all_chunks)} total chunks to ChromaDB...")
        
        # Smaller batches to avoid rate limits
        import time
        batch_size = 50
        for i in range(0, len(all_chunks), batch_size):
            batch_end = min(i + batch_size, len(all_chunks))
            
            # Retry with backoff on rate limit
            for attempt in range(5):
                try:
                    collection.add(
                        documents=all_chunks[i:batch_end],
                        ids=all_ids[i:batch_end],
                        metadatas=all_metadatas[i:batch_end]
                    )
                    break
                except Exception as e:
                    if "429" in str(e) or "rate" in str(e).lower():
                        wait_time = 2 ** attempt
                        print(f"  Rate limited, waiting {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise
            
            if (i // batch_size + 1) % 20 == 0:
                print(f"  Added {batch_end}/{len(all_chunks)} chunks...")
        
        print(f"\n✓ Successfully indexed {len(all_chunks)} chunks!")
        print(f"  - Transcripts: {len(all_chunks) - article_chunks}")
        print(f"  - Sequoia Articles: {article_chunks}")
    else:
        print("No content was extracted from the files.")


if __name__ == "__main__":
    ingest_files()
