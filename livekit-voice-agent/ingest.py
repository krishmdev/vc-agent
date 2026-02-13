"""Build a knowledge-base index generation from data/ (podcast transcripts + Sequoia articles).

    uv run python ingest.py --embedder local    # all-MiniLM-L6-v2 from .models/, no network
    uv run python ingest.py --embedder openai   # text-embedding-3-small, needs OPENAI_API_KEY
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

import config
import rag
from embeddings import make_embedder

CHUNK_SIZE = 2000
CHUNK_OVERLAP = 400

# Only process txt files (podcast transcripts)
SUPPORTED_EXTENSIONS = {".txt"}

# Path to data directory
DATA_DIR = config.DATA_DIR
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
        r'/cookie', r'/careers', r'/contact', r'/tag/', r'/page/', r'/people/',
    ]
    # The crawl saved some pages several times under tracking-parameter URLs.
    seen_urls: set[str] = set()
    seen_content: set[str] = set()
    
    for page in pages:
        url = page.get('url', '')
        title = page.get('title', '')
        markdown = page.get('markdown', '')
        
        # Skip non-content pages
        if any(re.search(p, url, re.I) for p in skip_patterns):
            continue
        canonical = url.split('#')[0].split('?')[0].rstrip('/').lower()
        if canonical in seen_urls:
            continue
        
        # Skip short content (likely navigation pages)
        if not markdown or len(markdown) < 500:
            continue
        
        # Clean the markdown
        clean_md = clean_markdown(markdown)
        if len(clean_md) < 300:
            continue
        
        digest = hashlib.sha256(clean_md.encode('utf-8')).hexdigest()
        if digest in seen_content:
            continue
        seen_urls.add(canonical)
        seen_content.add(digest)

        # Extract title for source
        source = title.replace(' | Sequoia Capital', '').replace(' | Sequoia', '').strip()
        if not source:
            source = 'Sequoia Article'
        
        articles.append({
            'content': clean_md,
            'source': source,
            'url': url.split('?')[0].split('#')[0],
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


def chunk_text(text: str, source_name: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[str]:
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


def collect_chunks() -> tuple[list[str], list[str], list[dict]]:
    files = sorted(get_files_to_process())
    print(f"Found {len(files)} transcript file(s)")
    sequoia_articles = extract_sequoia_articles()

    all_chunks: list[str] = []
    all_ids: list[str] = []
    all_metadatas: list[dict] = []

    for file_path in files:
        content = read_file(file_path)
        if not content.strip():
            continue
        source_name = file_path.stem.replace("_", " ")
        for i, chunk in enumerate(chunk_text(content, source_name)):
            all_chunks.append(chunk)
            all_ids.append(f"transcript_{file_path.stem}_{i}")
            all_metadatas.append({"source": source_name, "type": "transcript", "chunk_index": i})
    transcript_chunks = len(all_chunks)
    print(f"  Created {transcript_chunks} chunks from transcripts")

    for idx, article in enumerate(sequoia_articles):
        for i, chunk in enumerate(chunk_text(article['content'], article['source'])):
            all_chunks.append(chunk)
            all_ids.append(f"sequoia_{idx}_{i}")
            meta = {"source": article['source'], "type": "website", "chunk_index": i}
            if article.get("url"):
                meta["url"] = article["url"]
            all_metadatas.append(meta)
    print(f"  Created {len(all_chunks) - transcript_chunks} chunks from Sequoia articles")
    return all_chunks, all_ids, all_metadatas


def corpus_sha256(chunks: list[str]) -> str:
    h = hashlib.sha256()
    for c in chunks:
        h.update(c.encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


def ingest_files(embedder_kind: str | None = None) -> str:
    embedder = make_embedder(embedder_kind)
    chunks, ids, metadatas = collect_chunks()
    if not chunks:
        raise SystemExit("No content was extracted from the files.")

    print(f"\nEmbedding {len(chunks)} chunks with {embedder.embedder_id}...")
    name = rag.build_generation(
        embedder,
        chunks,
        ids,
        metadatas,
        extra_metadata={
            "corpus_sha256": corpus_sha256(chunks),
            "chunking": json.dumps({"size": CHUNK_SIZE, "overlap": CHUNK_OVERLAP}),
        },
        batch_size=64 if embedder.slug.startswith("minilm") else 100,
    )
    print(f"\nIndexed {len(chunks)} chunks into {name} (now active for {embedder.slug})")
    return name


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--embedder", choices=["local", "openai"], default=None,
                        help="defaults to local in offline mode, KB_EMBEDDER (openai) in live mode")
    args = parser.parse_args()
    ingest_files(args.embedder)
