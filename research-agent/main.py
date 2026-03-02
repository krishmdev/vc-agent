import asyncio
import json
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import praw
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from google import genai
from google.genai import types
from pydantic import BaseModel

# Allow `uvicorn research-agent.main:app` from the repo root as well as from this directory.
sys.path.append(str(Path(__file__).resolve().parent))

import settings  # noqa: E402
from diagnostics import probe_egress  # noqa: E402
from founder_api import make_domain_classifier  # noqa: E402
from founder_api import router as founder_router  # noqa: E402
from guides import citations_for, make_guide_writer  # noqa: E402
from kb_client import KnowledgeBaseClient, KnowledgeBaseUnavailable  # noqa: E402
from prompts import build_context, build_deep_research_prompt  # noqa: E402
from research_providers import make_research_provider  # noqa: E402
from slide_generator import (  # noqa: E402
    generate_pitch_deck_with_manus,
    prepare_slide_data,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.research = make_research_provider()
    app.state.guides = make_guide_writer()
    app.state.classifier = make_domain_classifier()
    app.state.kb = KnowledgeBaseClient(settings.KB_SERVICE_URL)
    app.state.http = httpx.AsyncClient(timeout=30)
    print(f"research agent mode={settings.MODE} research={app.state.research.name}")
    yield
    # Shutdown: cancel jobs still running (a live deep-research job also cancels its remote run)
    # and wait for them, so none is left writing to a closed client.
    jobs = list(running_jobs)
    for job in jobs:
        job.cancel()
    await asyncio.gather(*jobs, return_exceptions=True)
    await app.state.kb.aclose()
    await app.state.http.aclose()


app = FastAPI(lifespan=lifespan)
app.include_router(founder_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# --- Data Models ---

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str  # User's input or "Start research"
    # Context (optional, primarily for the first turn)
    idea: Optional[str] = None
    problem: Optional[str] = None
    customer: Optional[str] = None
    product: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    task_id: str  # To poll for the specific answer
    status: str
    message: str

class PollResponse(BaseModel):
    status: str  # queued, running, completed, failed
    content: Optional[str] = None
    error: Optional[str] = None
    kind: Optional[str] = None  # deep_research | follow_up | reachout | slides
    provider: Optional[str] = None
    progress: List[str] = []
    elapsed_s: Optional[float] = None

class CustomerReachoutRequest(BaseModel):
    icp_description: str
    customer_type: str  # "B2C" or "B2B"

class CustomerReachoutResponse(BaseModel):
    task_id: str
    status: str
    message: str

class SlideGenerationRequest(BaseModel):
    modules: Dict[str, Any]  # Dashboard modules data
    idea: str  # Initial startup idea for fallback

class SlideGenerationResponse(BaseModel):
    task_id: str
    status: str
    message: str

# --- In-Memory Stores ---
# In production, use Redis or Postgres
chat_sessions: Dict[str, List[Dict[str, str]]] = {}  # session_id -> history [{role: user/assistant, content: ...}]
active_tasks: Dict[str, Dict[str, Any]] = {}  # task_id -> {status, content, progress, ...}
sessions_in_flight: set[str] = set()  # sessions whose first (deep research) turn is still running

MAX_PROGRESS_NOTES = 12
TERMINAL = ("completed", "failed", "cancelled")
# Finished tasks are dropped after an hour, and the oldest go first past this many.
TASK_TTL_S = 3600
MAX_TASKS = 500
# At most this many jobs run at once; past it new work gets a 503. A job still running after
# RUNNING_TTL_S is cancelled (the provider's own timeout is 30 minutes, so this is a backstop).
MAX_RUNNING_JOBS = 16
RUNNING_TTL_S = 2 * 3600
# Chat histories idle this long are dropped, and the least recently used go first past the cap.
SESSION_TTL_S = 6 * 3600
MAX_SESSIONS = 500
session_touched: Dict[str, float] = {}

# Deep research can run for many minutes, longer than a request cycle, so jobs are plain asyncio
# tasks on the server's loop. Keep references so they aren't garbage collected mid-run.
running_jobs: set[asyncio.Task] = set()
jobs_by_task: Dict[str, asyncio.Task] = {}


def start_job(task_id: str, coro) -> None:
    async def guarded():
        try:
            await coro
        except asyncio.CancelledError:
            if active_tasks.get(task_id, {}).get("status") not in TERMINAL:
                update_task(task_id, status="cancelled", error="Cancelled before it finished: the server stopped or the job ran too long.")
            raise

    job = asyncio.create_task(guarded())
    running_jobs.add(job)
    jobs_by_task[task_id] = job

    def done(j: asyncio.Task) -> None:
        running_jobs.discard(j)
        jobs_by_task.pop(task_id, None)

    job.add_done_callback(done)


def evict_tasks(now: float | None = None) -> None:
    now = time.monotonic() if now is None else now
    for tid, t in list(active_tasks.items()):
        if t["status"] in TERMINAL:
            if now - t.get("finished", now) > TASK_TTL_S:
                del active_tasks[tid]
        elif now - t["started"] > RUNNING_TTL_S and tid in jobs_by_task:
            jobs_by_task[tid].cancel()  # the job marks itself cancelled
    overflow = len(active_tasks) - MAX_TASKS
    if overflow > 0:
        finished = sorted((t.get("finished", t["started"]), tid) for tid, t in active_tasks.items() if t["status"] in TERMINAL)
        for _, tid in finished[:overflow]:
            del active_tasks[tid]
    evict_sessions(now)


def evict_sessions(now: float) -> None:
    idle = [sid for sid in chat_sessions if sid not in sessions_in_flight]
    for sid in idle:
        if now - session_touched.get(sid, now) > SESSION_TTL_S:
            chat_sessions.pop(sid, None)
            session_touched.pop(sid, None)
    overflow = len(chat_sessions) - MAX_SESSIONS
    if overflow > 0:
        oldest = sorted((session_touched.get(sid, 0.0), sid) for sid in chat_sessions if sid not in sessions_in_flight)
        for _, sid in oldest[:overflow]:
            chat_sessions.pop(sid, None)
            session_touched.pop(sid, None)


def new_task(prefix: str, kind: str, provider: str | None = None) -> str:
    evict_tasks()
    if len(running_jobs) >= MAX_RUNNING_JOBS:
        raise HTTPException(status_code=503, detail="Too many jobs running; try again in a few minutes")
    task_id = f"{prefix}_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    active_tasks[task_id] = {
        "status": "queued",
        "kind": kind,
        "provider": provider,
        "progress": [],
        "started": time.monotonic(),
    }
    return task_id


def update_task(task_id: str, **fields: Any) -> None:
    task = active_tasks.get(task_id)
    if task is None:  # evicted while the job ran
        return
    task.update(fields)
    if fields.get("status") in TERMINAL:
        task["finished"] = time.monotonic()


def gemini_client() -> genai.Client | None:
    key = settings.gemini_api_key()
    return genai.Client(api_key=key) if key else None


# --- Research chat ---

async def run_research_turn(task_id: str, session_id: str, user_message: str, context: str, first_turn: bool):
    research = app.state.research

    def on_progress(stage: str, note: str | None = None) -> None:
        task = active_tasks.get(task_id)
        if task is None:
            return
        task["status"] = stage
        if note:
            task["progress"] = (task["progress"] + [note])[-MAX_PROGRESS_NOTES:]

    try:
        history = chat_sessions.get(session_id, [])
        if first_turn:
            prompt = build_deep_research_prompt(history, context, user_message)
            print(f"Starting deep research for task {task_id} (session {session_id}) via {research.name}")
            content = await research.deep_research(prompt, context=context, on_progress=on_progress)
        else:
            update_task(task_id, status="running")
            print(f"Starting follow-up for task {task_id} (session {session_id}) via {research.name}")
            content = await research.follow_up(history, user_message, context)

        update_task(task_id, status="completed", content=content)
        session = chat_sessions.setdefault(session_id, [])
        session.append({"role": "user", "content": user_message})
        session.append({"role": "assistant", "content": content})
        session_touched[session_id] = time.monotonic()
    except Exception as e:
        print(f"Error in research turn: {e}")
        update_task(task_id, status="failed", error=str(e))
    finally:
        sessions_in_flight.discard(session_id)


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    chat_sessions.setdefault(session_id, [])
    session_touched[session_id] = time.monotonic()

    context_str = build_context(request.idea, request.problem, request.customer, request.product)
    # A follow-up sent before the first turn finishes would otherwise start a second paid run.
    if session_id in sessions_in_flight:
        raise HTTPException(status_code=409, detail="The first research turn for this session is still running")

    # First turn runs the deep research agent; later turns are fast grounded follow-ups.
    first_turn = len(chat_sessions[session_id]) == 0
    task_id = new_task("msg", "deep_research" if first_turn else "follow_up", app.state.research.name)
    if first_turn:
        sessions_in_flight.add(session_id)  # before the job starts, so a quick follow-up sees it
    start_job(task_id, run_research_turn(task_id, session_id, request.message, context_str, first_turn))

    return ChatResponse(
        session_id=session_id,
        task_id=task_id,
        status="queued",
        message="Research started"
    )

@app.get("/chat/status/{task_id}", response_model=PollResponse)
async def get_task_status(task_id: str):
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = active_tasks[task_id]
    return PollResponse(
        status=task.get("status", "unknown"),
        content=task.get("content"),
        error=task.get("error"),
        kind=task.get("kind"),
        provider=task.get("provider"),
        progress=task.get("progress", []),
        elapsed_s=round(time.monotonic() - task["started"], 1) if "started" in task else None,
    )


# --- Resource drawer: guides grounded in the Sequoia knowledge base ---

class ResourceArticleRequest(BaseModel):
    question: str
    module: str
    context: Optional[str] = None

class ResourceArticleResponse(BaseModel):
    content: str
    citations: List[Dict[str, Any]] = []
    embedder_id: Optional[str] = None
    writer: Optional[str] = None

class ResourceChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] # [{"role": "user", "content": "..."}]
    resource_context: str

class ResourceChatResponse(BaseModel):
    message: str
    citations: List[Dict[str, Any]] = []


async def retrieve(query: str, top_k: int = 4):
    try:
        return await app.state.kb.search(query, top_k=top_k)
    except KnowledgeBaseUnavailable as e:
        if settings.OFFLINE:
            raise HTTPException(status_code=503, detail=str(e))
        # Live mode can still write an ungrounded guide with Google Search.
        print(f"Knowledge base unavailable, continuing without it: {e}")
        return []


@app.post("/generate_resource_article", response_model=ResourceArticleResponse)
async def generate_resource_article(request: ResourceArticleRequest):
    writer = app.state.guides
    if writer is None:
        raise HTTPException(status_code=500, detail="API Key missing")

    passages = await retrieve(request.question)
    try:
        content = await writer.write_guide(request.question, passages)
    except Exception as e:
        print(f"Error generating resource article: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    if not content:
        raise HTTPException(status_code=500, detail="Failed to generate content")
    return ResourceArticleResponse(
        content=content,
        citations=citations_for(passages),
        embedder_id=app.state.kb.embedder_id if passages else None,
        writer=writer.name,
    )


@app.post("/resource_chat", response_model=ResourceChatResponse)
async def resource_chat_endpoint(request: ResourceChatRequest):
    writer = app.state.guides
    if writer is None:
        raise HTTPException(status_code=500, detail="API Key missing")

    passages = await retrieve(request.message, top_k=3)
    try:
        message = await writer.answer(request.message, request.history, request.resource_context, passages)
    except Exception as e:
        print(f"Error in resource chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return ResourceChatResponse(message=message, citations=citations_for(passages))


# --- Customer reach-out ---

OFFLINE_REACHOUT_NOTE = (
    "Customer discovery calls Reddit, Apollo and Gemini, so it is turned off in offline mode."
)


async def generate_json(client: genai.Client, prompt: str) -> Any:
    resp = await client.aio.models.generate_content(
        model=settings.UTILITY_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(resp.text)


def search_subreddits(keywords: List[str], client_id: str, client_secret: str, user_agent: str, limit: int = 2):
    """Blocking PRAW calls; run it in the threadpool."""
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        check_for_updates=False
    )
    found = []
    seen = set()
    for kw in keywords:
        for sub in reddit.subreddits.search(kw, limit=2):
            if sub.display_name in seen:
                continue
            seen.add(sub.display_name)
            found.append({
                "name": sub.display_name,
                "url": sub.url,
                "description": (sub.public_description or "")[:200],
            })
            if len(found) >= limit:
                return found
    return found


async def run_b2c_pipeline(client: genai.Client, icp_description: str) -> Dict[str, Any]:
    # Step 1: Extract keywords using Gemini
    keyword_prompt = f"""
    Extract 3-5 high-relevance search keywords to find Reddit communities for this ICP: "{icp_description}".
    Make them broad enough to match subreddit names or topics (e.g., "smallbusiness", "marketing", "entrepreneur").
    Return JSON: `{{"keywords": ["kw1", "kw2"]}}`
    """
    keywords = (await generate_json(client, keyword_prompt)).get("keywords", [])

    forums = []
    reddit_client_id = os.environ.get("REDDIT_CLIENT_ID")
    reddit_client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    reddit_user_agent = os.environ.get("REDDIT_USER_AGENT", "BrownHacksResearchAgent/1.0")

    if reddit_client_id and reddit_client_secret:
        try:
            # Step 2: Search Reddit (PRAW is synchronous)
            subs = await run_in_threadpool(
                search_subreddits, keywords, reddit_client_id, reddit_client_secret, reddit_user_agent
            )
            # Step 3: Generate a strategy for each community
            for sub in subs:
                strat_prompt = f"""
                Context: Subreddit r/{sub['name']} - {sub['description']}...
                ICP: {icp_description}

                Write a detailed 2-3 sentence authentic outreach strategy for this specific community.
                """
                strat_resp = await client.aio.models.generate_content(
                    model=settings.UTILITY_MODEL, contents=strat_prompt
                )
                forums.append({
                    "name": f"r/{sub['name']}",
                    "url": f"https://www.reddit.com{sub['url']}",
                    "strategy": (strat_resp.text or "").strip(),
                })
        except Exception as reddit_err:
            print(f"Reddit API Error: {reddit_err}")
            forums.append({"name": "Reddit API Error", "url": "#", "strategy": "Please check REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET env vars."})
    else:
        forums.append({"name": "Config Missing", "url": "#", "strategy": "Please set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env"})

    # Step 4: Generate offline suggestions
    offline_prompt = f"""
    Based on this ICP: "{icp_description}"
    Suggest 2-3 specific types of offline places/venues where this person could be found in person.
    Return JSON: `{{"offline": ["Place 1", "Place 2"]}}`
    """
    offline_suggestions = (await generate_json(client, offline_prompt)).get("offline", [])
    return {"forums": forums, "offline": offline_suggestions}


async def apollo_search(http: httpx.AsyncClient, url: str, payload: Dict[str, Any], api_key: str) -> Dict[str, Any] | None:
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "X-Api-Key": api_key
    }
    try:
        resp = await http.post(url, json=payload, headers=headers)
    except httpx.HTTPError as e:
        print(f"Apollo request error ({url}): {e}")
        return None
    print(f"Apollo {url.rsplit('/', 1)[-1]} response status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Apollo error response: {resp.text[:500]}")
        return None
    return resp.json()


async def run_b2b_pipeline(client: genai.Client, icp_description: str) -> Dict[str, Any]:
    apollo_api_key = os.environ.get("APOLLO_API_KEY")
    print(f"B2B Pipeline started. APOLLO_API_KEY present: {bool(apollo_api_key)}")

    # Step 1: Parse ICP to Apollo Params using Gemini
    parse_prompt = f"""
    Extract search parameters for Apollo.io API from this ICP: "{icp_description}"

    Return JSON:
    {{
        "job_titles": ["title1", "title2"],
        "keywords": ["keyword1", "keyword2"],
        "seniorities": ["manager", "director", "vp", "c_suite"],
        "industries": ["industry1"],
        "min_employees": 10,
        "max_employees": 1000
    }}
    """
    params = await generate_json(client, parse_prompt)
    print(f"Parsed ICP params: {params}")

    contacts = []
    companies = []

    if apollo_api_key:
        http = app.state.http
        people_payload = {
            "q_keywords": ",".join(params.get("keywords", [])),
            "person_titles": params.get("job_titles", []),
            "person_seniorities": params.get("seniorities", []),
            "page": 1,
            "per_page": 10
        }
        people = await apollo_search(http, "https://api.apollo.io/v1/mixed_people/search", people_payload, apollo_api_key)
        for p in (people or {}).get("people", []):
            contacts.append({
                "name": f"{p.get('first_name')} {p.get('last_name')}",
                "title": p.get("title"),
                "company": (p.get("organization") or {}).get("name"),
                "email": p.get("email") or "Not available",
                "note": f"Matches {p.get('title')} role"
            })

        org_payload = {
            "q_organization_keyword_tags": params.get("industries", []),
            "organization_num_employees_ranges": [f"{params.get('min_employees')},{params.get('max_employees')}"],
            "page": 1,
            "per_page": 5
        }
        orgs = await apollo_search(http, "https://api.apollo.io/v1/mixed_companies/search", org_payload, apollo_api_key)
        for o in (orgs or {}).get("organizations", []):
            companies.append({
                "name": o.get("name"),
                "industry": (o.get("primary_industry") or {}).get("industry") or "Unknown",
                "size": o.get("estimated_num_employees"),
                "location": f"{o.get('city')}, {o.get('country')}",
                "website": o.get("website_url"),
                "note": "Fits industry and size criteria"
            })

    # Fallback: Generate sample data using Gemini if Apollo returned nothing
    if not contacts and not companies:
        print("Apollo returned no results. Generating sample data with Gemini.")
        fallback_prompt = f"""
        Based on this ICP: "{icp_description}"
        Generate sample B2B target data.

        Return JSON:
        {{
            "key_contacts": [
                {{"name": "Sample Name", "title": "Sample Title", "company": "Sample Company", "email": "sample@example.com", "note": "Generated sample based on ICP"}}
            ],
            "target_companies": [
                {{"name": "Sample Company", "industry": "Sample Industry", "size": 100, "location": "Sample Location", "website": "https://example.com", "note": "Generated sample based on ICP"}}
            ]
        }}
        """
        fallback_data = await generate_json(client, fallback_prompt)
        contacts = fallback_data.get("key_contacts", [])
        companies = fallback_data.get("target_companies", [])

    if not apollo_api_key:
        # Graceful degradation when the key is missing
        contacts.append({"name": "No Apollo API Key", "title": "Check .env", "company": "System", "email": "", "note": "Please set APOLLO_API_KEY"})
        companies.append({"name": "No Apollo API Key", "industry": "System", "size": 0, "location": "Local", "website": "", "note": "Please set APOLLO_API_KEY"})

    return {"key_contacts": contacts, "target_companies": companies}


def offline_reachout(customer_type: str) -> Dict[str, Any]:
    if customer_type == "B2B":
        note = {"name": "Offline mode", "title": "", "company": "", "email": "", "note": OFFLINE_REACHOUT_NOTE}
        return {"key_contacts": [note], "target_companies": []}
    return {"forums": [{"name": "Offline mode", "url": "#", "strategy": OFFLINE_REACHOUT_NOTE}], "offline": []}


async def run_customer_reachout_task(task_id: str, icp_description: str, customer_type: str):
    update_task(task_id, status="running")
    try:
        if settings.OFFLINE:
            result_data = offline_reachout(customer_type)
        else:
            client = gemini_client()
            if client is None:
                update_task(task_id, status="failed", error="GEMINI_API_KEY missing")
                return
            if customer_type == "B2C":
                result_data = await run_b2c_pipeline(client, icp_description)
            elif customer_type == "B2B":
                result_data = await run_b2b_pipeline(client, icp_description)
            else:
                result_data = {}

        update_task(task_id, status="completed", content=json.dumps(result_data))
    except Exception as e:
        print(f"Error in customer reachout: {e}")
        update_task(task_id, status="failed", error=str(e))

@app.post("/customer-reachout", response_model=CustomerReachoutResponse)
async def customer_reachout_endpoint(request: CustomerReachoutRequest):
    task_id = new_task("reachout", "reachout")
    start_job(task_id, run_customer_reachout_task(task_id, request.icp_description, request.customer_type))

    return CustomerReachoutResponse(
        task_id=task_id,
        status="queued",
        message="Customer search started"
    )

@app.get("/health")
async def health_check():
    return {"status": "ok", "mode": settings.MODE, "research_provider": app.state.research.name}


# --- Slide Generation ---

async def run_slide_generation_task(task_id: str, modules: Dict[str, Any], idea: str):
    """Background task for generating pitch deck slides."""
    update_task(task_id, status="running")
    try:
        print(f"Starting slide generation for task {task_id}")
        if settings.OFFLINE:
            update_task(task_id, status="failed", error="Pitch deck generation needs Gemini; it is off in offline mode.")
            return

        gemini = gemini_client()
        if gemini is None:
            update_task(task_id, status="failed", error="GEMINI_API_KEY not configured")
            return

        # Extracts dashboard values and fills gaps with Gemini, concurrently.
        slide_data = await prepare_slide_data(modules, idea, gemini)
        print(f"Prepared slide data with {len(slide_data)} slides")

        # Try Manus first, fall back to Gemini
        result = await generate_pitch_deck_with_manus(modules, idea, gemini, slide_data, http=app.state.http)

        if result.get("status") == "completed":
            update_task(task_id, status="completed", content=json.dumps(result.get("data", {})), type=result.get("type", "json"))
        elif result.get("status") == "failed":
            update_task(task_id, status="failed", error=result.get("error", "Unknown error"))
        else:
            # Manus returned a task_id for async processing
            update_task(task_id, status="completed", content=json.dumps(result), type="manus_task")

    except Exception as e:
        print(f"Error in slide generation: {e}")
        update_task(task_id, status="failed", error=str(e))


@app.post("/generate-slides", response_model=SlideGenerationResponse)
async def generate_slides_endpoint(request: SlideGenerationRequest):
    """Generate a Sequoia-style pitch deck from dashboard data."""
    task_id = new_task("slides", "slides")
    start_job(task_id, run_slide_generation_task(task_id, request.modules, request.idea))

    return SlideGenerationResponse(
        task_id=task_id,
        status="queued",
        message="Generating pitch deck..."
    )


if settings.DIAGNOSTICS:
    @app.get("/_diag/egress")
    async def egress_diagnostics():
        return await probe_egress("research-agent")

    @app.get("/_diag/providers")
    async def provider_diagnostics():
        return {
            "mode": settings.MODE,
            "research": app.state.research.name,
            "guides": app.state.guides.name if app.state.guides else None,
            "classifier": app.state.classifier.name,
            "kb_service": settings.KB_SERVICE_URL,
            "gemini_key_visible": bool(os.environ.get("GEMINI_API_KEY")),
        }
