# Sequoia Startup Mentor - RAG Voice Agent

A real-time voice AI assistant that acts as a startup mentor, drawing wisdom from Sequoia Capital's philosophy and insights. Built with LiveKit Agents, OpenAI GPT-4o, and ChromaDB.

## Features

- **Terminal-Based Interaction**: Low-latency conversation directly in your terminal.
- **RAG (Retrieval-Augmented Generation)**: Grounded in Sequoia Capital's knowledge base.
- **Mentor Persona**: Configured to think and speak like a Sequoia executive.

## Prerequisites

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** (highly recommended for dependency management)
- **API Keys**: OpenAI, AssemblyAI, Cartesia
- **LiveKit Cloud Project** (for the backend infrastructure)

## Setup Instructions

### 1. Clone and Install

```bash
git clone <your-repo-url>
cd livekit-voice-agent
uv sync
```

### 2. Configure Environment

Create a `.env.local` file in the root directory:

```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

OPENAI_API_KEY=your-openai-key
ASSEMBLYAI_API_KEY=your-assemblyai-key
CARTESIA_API_KEY=your-cartesia-key
```

### 3. Ingest Knowledge Base

The Sequoia data is already included in the `data/` folder. Run the ingestion script to build the vector database:

```bash
uv run ingest.py
```

### 4. Run the Agent

Interact with the mentor directly in your terminal:

```bash
uv run agent.py console
```

## Project Structure

- `agent.py`: Main LiveKit agent logic and persona configuration.
- `ingest.py`: Script to chunk and index files into ChromaDB.
- `rag.py`: RAG helper for semantic search.
- `data/`: Contains `sequoia_data.json`.

## How it Works

1. **Ingestion**: `ingest.py` splits the Sequoia data into chunks and generates embeddings using `all-MiniLM-L6-v2`.
2. **Retrieval**: When you ask a question, the agent searches ChromaDB for the most relevant Sequoia insights.
3. **Generation**: GPT-4o uses the retrieved context to provide mentored advice in a natural, conversational style.
