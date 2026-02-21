#!/bin/zsh

# Launchpad Startup Script
# Run with: zsh start.sh

echo "Starting Launchpad (live mode)..."

# Get the directory where this script is located
SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to cleanup on exit
cleanup() {
    echo "\nShutting down all services..."
    kill $FRONTEND_PID $RESEARCH_PID $LIVEKIT_PID $KB_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Knowledge base + text transport (the research agent's guides query it)
echo "${BLUE}[1/4]${NC} Starting knowledge-base server on port 8001..."
cd "$SCRIPT_DIR/livekit-voice-agent"
uv run uvicorn server:app --port 8001 &
KB_PID=$!

# Start Research Agent (FastAPI backend). No --reload: tasks and sessions live in memory.
echo "${BLUE}[2/4]${NC} Starting Research Agent on port 8000..."
cd "$SCRIPT_DIR/research-agent"
uv run uvicorn main:app --port 8000 &
RESEARCH_PID=$!

# Start LiveKit Voice Agent
echo "${BLUE}[3/4]${NC} Starting LiveKit Voice Agent..."
cd "$SCRIPT_DIR/livekit-voice-agent"
uv run agent.py dev &
LIVEKIT_PID=$!

# Start Frontend (Next.js)
echo "${BLUE}[4/4]${NC} Starting Frontend on port 3000..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "${GREEN}All services started.${NC}"
echo ""
echo "   Frontend:        http://localhost:3000"
echo "   Research Agent:  http://localhost:8000"
echo "   KB / text chat:  http://localhost:8001"
echo "   LiveKit Agent:   Running in background"
echo ""
echo "Press Ctrl+C to stop all services."
echo ""

# Wait for any process to exit
wait
