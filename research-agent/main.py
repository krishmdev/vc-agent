from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import time
import uuid
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env.local")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    status: str  # processing, completed, failed
    content: Optional[str] = None
    error: Optional[str] = None

# --- In-Memory Stores ---
# In production, use Redis or Postgres
chat_sessions: Dict[str, List[Dict[str, str]]] = {}  # session_id -> history [{role: user/assistant, content: ...}]
active_tasks: Dict[str, Dict[str, Any]] = {}  # task_id -> {status, content, session_id}

# --- System Prompt ---
SYSTEM_INSTRUCTION = """
You are the "Problem Space Specialist", a Senior Market Researcher and Early-Stage Investor Analyst (Sequoia/Bessemer style).

Your goal is to rigorously research the startup problem space to validate if it is worth solving.
You operate in a turn-based conversational mode. 

PRIMARY OUTPUT STRUCTURE:
When asked to analyze a problem space, you MUST structure your response as follows use Markdown:

# MARKET SPACE ASSESSMENT
1. Market Landscape & Key Players
   - Current dominant players (position, share)
   - Emerging challengers
   - Constraints: Max 5-7 players. 1 sentence each.
2. Market Dynamics & Trends
   - Tech shifts, Business model evolution, Customer behavior
   - Major events (M&A, bankruptcies) in last 12-18 months
3. Market Opportunity Analysis
   - TAM/SAM/SOM estimates
   - Investment climate (Funding, Valuations)
   - Whitespace identification
   - Saturation indicators (CAC, Churn)
4. Barriers & Challenges
   - Regulatory, Operational, Competitive Moats, Economic

# SOLUTION–MARKET FIT ANALYSIS
5. Positioning & Differentiation
   - User's solution vs incumbents
   - Unique Value Prop
6. Viability Assessment
   - Why Now? (Timing)
   - Strengths vs Risks/Failure Modes
7. Strategic Recommendations
   - Quick wins, Pivots, Gaps, Partnerships
   - Limit to top 3-5 actionable items

# EXECUTIVE SUMMARY
- 500-600 words max.
- Verdict: Attractive / Questionable / Avoid
- Top 3 Insights
- Primary Recommendation

# RED FLAGS
- Explicitly list concerning signals. Do not soften bad news.

EVIDENCE & QUALITY:
- Cite 1-2 credible sources for every major claim using IN-LINE Markdown links.
- Format: `[Source Name](URL)`. Example: "The market grew 20% [TechCrunch](https://techcrunch.com)..."
- CRITICAL: Do NOT create a separate "Sources", "References", or "Bibliography" section at the end. All links must be embedded in the text.
- Distinguish factual vs speculative.
- Be skeptical, precise, and high-signal. Do not be encouraging by default.

SOURCE QUALITY REQUIREMENTS:

PRIORITIZE (in order):
1. **Primary sources**: Company financial filings (10-Ks, S-1s), official company blogs, government data
2. **Industry research**: Gartner, Forrester, CB Insights, PitchBook, McKinsey, BCG, a16z research
3. **Financial/business news**: WSJ, Financial Times, Bloomberg, Reuters, The Information
4. **Trade publications**: Industry-specific authoritative sources (TechCrunch for tech, etc.)
5. **Academic research**: Peer-reviewed papers, university research centers

AVOID:
- Content farms, SEO spam sites, listicles
- Anonymous blogs or unattributed sources
- Press releases as sole source (ok as supplementary)
- Sites with paywalls you can't verify (cite but flag as unverified)
- Reddit, Quora, or forum posts (unless specifically seeking user sentiment)
- Marketing agencies' "research reports" that are thinly veiled ads

VERIFICATION:
- Cross-reference claims with at least 2 independent sources for critical facts
- For statistics, trace back to the original research/data source
- Flag confidence level: [High confidence - multiple credible sources] vs [Limited data - single source]
- When citing, include: source name, date, and brief credibility note if not obvious

When searching:
- Use queries that specify source types: "market size according to Gartner" not just "market size"
- Request specific publications: "venture funding trends Bloomberg Reuters"
- Use advanced operators: site:sec.gov for filings
- Search for original research: "primary research [topic]" or "[topic] white paper"

During research:
- When you find a statistic, search for its original source
- If multiple sources cite the same data, find the original
- Prefer dated, attributed, and methodologically transparent sources

After generating the research, review all sources and:

1. Remove any citations from:
   - Sites you can't verify are credible
   - Sources older than 18 months (unless historical context)
   - Circular citations (Site A citing Site B citing Site A)

2. For each remaining source, add a credibility tag:
   [Primary source] [Industry analyst] [Major publication] [Limited verification]

3. If a key finding only has weak sources, either:
   - Flag it as "reported by X but unverified"
   - Remove it and note the gap
   - Search specifically for better sources on that point

4. Ensure each major section has at least 2 different source types

CITATION & FORMATTING RULES (CRITICAL):

1. **NO BIBLIOGRAPHIES**: Do NOT create a "Sources", "References", or "Bibliography" section at the end.
2. **NO NUMERIC CITATIONS**: Do NOT use `[1]`, `[cite: 1]`, or `(Source 1)` format.
3. **INLINE LINKS ONLY**: Embed links directly into the text using Markdown `([Source Name](URL))`.

✅ **CORRECT FORMAT**:
"The pet services market is projected to reach $2B by 2025 ([TechCrunch](https://techcrunch.com/pet-market)), driven significantly by the rise in pet adoption during the pandemic ([Bloomberg](https://bloomberg.com/reports/pets))."

❌ **INCORRECT FORMAT**:
"The pet services market is projected to reach $2B by 2025 [1].
...
Sources:
1. TechCrunch"

4. **Verify Every Link**: Ensure the URL is valid and relevant.
5. **Coverage**: Every major statistic or specific claim MUST have an inline link immediately following it.

INTERACTION STYLE:
- Remember prior turns.
- If the user provides new info, refine your analysis.
- If the user asks a specific question, answer it directly but keep the "Problem Space" lens.
"""

FAST_CHAT_INSTRUCTION = """
You are a Market Research Assistant helping founders understand their problem space. You've already provided a comprehensive market analysis, and now you're answering follow-up questions.

CONTEXT:
You have access to the full market research report that was previously generated, which includes:
- Market landscape, key players, and competitive dynamics
- Market trends, opportunities, and barriers
- Analysis of the founder's specific solution and its fit
- Strategic recommendations

YOUR ROLE:
- Answer follow-up questions conversationally and directly
- Draw from the research already conducted, but search for new information if the question goes beyond what was covered
- Be concise but thorough - aim for clarity over comprehensiveness
- Always cite sources when making specific claims
- If you don't know something or the research didn't cover it, say so and offer to search for more information

GUIDELINES:
1. **Be direct**: Lead with the answer, then provide supporting detail
2. **Stay grounded**: Reference specific findings from the research when relevant
3. **Be honest about gaps**: If something wasn't covered or you're uncertain, acknowledge it
4. **Offer depth optionally**: Give a clear answer first, then ask if they want more detail
5. **Connect dots**: Help the founder see how different pieces of research relate to their question
6. **Be balanced**: Don't sugarcoat concerns, but also highlight opportunities fairly

TYPES OF QUESTIONS YOU MIGHT GET:
- Clarification: "What did you mean by X?"
- Deep dives: "Can you tell me more about competitor Y?"
- Application: "How would this trend affect my pricing strategy?"
- Challenges: "I disagree with your assessment of Z - what am I missing?"
- New angles: "What about market segment A that wasn't mentioned?"
- Tactical: "Should I target enterprise or SMB first?"

RESPONSE STYLE:
- Conversational, not formal report writing
- Use natural paragraphs, not bullet points (unless listing specific items makes sense)
- Include 1-2 relevant IN-LINE links when making specific claims: ([Source](URL)).
- Do NOT add a "Sources" list at the bottom.
- Keep responses 150-300 words unless the question clearly needs more depth
- If you need to search for new information, explain what you're looking for and why

WHAT TO AVOID:
- Don't restate large portions of the original research unless asked
- Don't be defensive if the founder challenges findings
- Don't make up information - cite sources or acknowledge uncertainty
- Don't overload with caveats - be confidently helpful while noting limitations
- Don't give investment advice or guarantees about success

Remember: You're a research partner, not a decision-maker. Your job is to inform, not prescribe.
"""
# --- Logic ---

def run_deep_research_task(task_id: str, session_id: str, user_message: str, context: str):
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            active_tasks[task_id] = {"status": "failed", "error": "API Key missing"}
            return

        client = genai.Client(api_key=api_key)
        
        # Build History Context
        history = chat_sessions.get(session_id, [])
        formatted_history = ""
        for msg in history:
            formatted_history += f"{msg['role'].upper()}: {msg['content']}\n\n"
            
        # Add current turn
        full_prompt = f"""
        {SYSTEM_INSTRUCTION}
        
        CONVERSATION HISTORY:
        {formatted_history}
        
        CURRENT CONTEXT:
        {context}
        
        USER MESSAGE:
        {user_message}
        
        Please provide your response.
        """

        print(f"Starting Deep Research for task {task_id} (Session {session_id})...")
        
        interaction = client.interactions.create(
            input=full_prompt,
            agent='deep-research-pro-preview-12-2025',
            background=True
        )
        
        # Poll the interaction
        while True:
            interaction = client.interactions.get(interaction.id)
            if interaction.status == "completed":
                if interaction.outputs:
                    content = interaction.outputs[-1].text
                    
                    # Update Task
                    active_tasks[task_id] = {
                        "status": "completed",
                        "content": content
                    }
                    
                    # Update Session History
                    chat_sessions[session_id].append({"role": "user", "content": user_message})
                    chat_sessions[session_id].append({"role": "assistant", "content": content})
                else:
                    active_tasks[task_id] = {"status": "failed", "error": "No output"}
                break
            elif interaction.status == "failed":
                active_tasks[task_id] = {"status": "failed", "error": str(interaction.error)}
                break
            
            time.sleep(10) # Simple polling delay

    except Exception as e:
        print(f"Error in deep research: {e}")
        active_tasks[task_id] = {"status": "failed", "error": str(e)}

def run_fast_chat_task(task_id: str, session_id: str, user_message: str, context: str):
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            active_tasks[task_id] = {"status": "failed", "error": "API Key missing"}
            return

        client = genai.Client(api_key=api_key)
        
        # Build History for Context
        history = chat_sessions.get(session_id, [])
        contents = []
        
        # Add System Instruction as first part of history or config? 
        # For generate_content, we usually pass system_instruction in config.
        
        # Convert history to API format
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            ))
            
        # Add current message with context instructions
        prompt_text = f"""
        User Message: {user_message}
        
        Context (Problem Space Data from initial research):
        {context}
        """
        
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt_text)]
        ))

        print(f"Starting Fast Chat for task {task_id} (Session {session_id})...")
        
        response = client.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                tools=[types.Tool(
                    google_search=types.GoogleSearch()
                )],
                system_instruction=FAST_CHAT_INSTRUCTION
            )
        )
        
        content = response.text
        
        # Update Task
        active_tasks[task_id] = {
            "status": "completed",
            "content": content
        }
        
        # Update Session History
        chat_sessions[session_id].append({"role": "user", "content": user_message})
        chat_sessions[session_id].append({"role": "assistant", "content": content})

    except Exception as e:
        print(f"Error in fast chat: {e}")
        active_tasks[task_id] = {"status": "failed", "error": str(e)}

# --- Resource Article Generation Logic ---

class ResourceArticleRequest(BaseModel):
    question: str
    module: str
    context: Optional[str] = None

class ResourceArticleResponse(BaseModel):
    content: str

@app.post("/generate_resource_article", response_model=ResourceArticleResponse)
async def generate_resource_article(request: ResourceArticleRequest):
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="API Key missing")

        client = genai.Client(api_key=api_key)

        prompt = f"""
        You are a Sequoia Capital partner creating an authoritative, tactical guide on: "{request.question}"

        Format this knowledge base content with the following requirements:

        **STRUCTURE:**
        - Use ## for main section headers (e.g., "## Core Principle")
        - Use ### for subsection headers only when absolutely necessary
        - Use **bold** only for key terms and important concepts (2-4 words max)
        - Separate sections with blank lines for breathing room
        - Each ## header should stand alone on its own line with one blank line after

        **CONTENT GUIDELINES:**
        - Keep paragraphs to 2-3 sentences maximum
        - Use bullet points (-) for lists of items, pitfalls, or non-sequential information
        - Start each bullet with a **bolded label:** followed by concise explanation (one sentence)
        - Use numbered lists (1., 2., 3.) only for sequential steps or prioritized actions
        - Remove redundant phrases and filler words—be direct and punchy
        - Focus on actionable insights over theory
        - Avoid nesting lists more than one level deep

        **VISUAL HIERARCHY:**
        - Main headers should stand alone on their own line
        - Add one blank line after headers
        - Add one blank line between distinct sections or paragraphs
        - Use bullet points to break up walls of text
        - Keep bold terms short (2-4 words max) for scannable emphasis

        **TONE:**
        - Direct and punchy
        - Avoid academic language and unnecessary superlatives
        - Use active voice
        - Keep it scannable and easy to digest
        - Write with authority and precision (Sequoia institutional tone)

        **REQUIRED STRUCTURE (in order):**
        ## Core Principle
        [2-3 sentence overview with one **key insight** highlighted]

        ## Why Founders Fail
        - **Label:** [Brief explanation]
        - **Label:** [Brief explanation]

        ## How to Execute
        [2-3 sentence intro]
        1. [Step one - concise]
        2. [Step two - concise]

        ## Key Signal
        [1-2 sentences on what metric or signal matters most]

        ## Example
        [Brief, concrete example illustrating the principle]

        **OUTPUT REQUIREMENTS:**
        Return ONLY clean markdown formatted content. No preamble, no meta-commentary.
        Start directly with ## Core Principle.
        Focus on clarity and scannability. Remove anything that doesn't directly help a founder make decisions.
        """

        response = client.models.generate_content(
            model='models/gemini-2.5-flash', # Using latest Gemini model
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(
                    google_search=types.GoogleSearch()
                )],
            )
        )

        if not response.text:
            raise HTTPException(status_code=500, detail="Failed to generate content")

        return ResourceArticleResponse(content=response.text)

    except Exception as e:
        print(f"Error generating resource article: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ResourceChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] # [{"role": "user", "content": "..."}]
    resource_context: str

class ResourceChatResponse(BaseModel):
    message: str

@app.post("/resource_chat", response_model=ResourceChatResponse)
async def resource_chat_endpoint(request: ResourceChatRequest):
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="API Key missing")

        client = genai.Client(api_key=api_key)

        # Build contents
        contents = []
        for msg in request.history:
             role = "user" if msg["role"] == "user" else "model"
             contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            ))

        # Add current message
        prompt_text = f"""
        You are a helpful assistant answering questions about a specific article.

        ARTICLE CONTEXT:
        {request.resource_context}

        USER QUESTION:
        {request.message}

        INSTRUCTIONS:
        - Answer strictly based on the provided article context + your general startup knowledge.
        - Be concise and helpful.
        """

        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt_text)]
        ))

        response = client.models.generate_content(
            model='models/gemini-2.5-flash',
            contents=contents
        )

        return ResourceChatResponse(message=response.text)

    except Exception as e:
        print(f"Error in resource chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, background_tasks: BackgroundTasks):
    # 1. Initialize Session if needed
    session_id = request.session_id or str(uuid.uuid4())
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []
    
    # 2. Construct Context string from optional fields
    context_parts = []
    if request.idea: context_parts.append(f"Idea: {request.idea}")
    if request.problem: context_parts.append(f"Problem: {request.problem}")
    if request.customer: context_parts.append(f"Customer: {request.customer}")
    if request.product: context_parts.append(f"Product: {request.product}")
    context_str = "\n".join(context_parts)
    
    # 3. Create Background Task
    task_id = f"msg_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    active_tasks[task_id] = {"status": "processing"}
    
    # Logic: If history is empty, use Deep Research (First Turn). 
    # If history exists, use Fast Chat (Follow-up).
    existing_history = chat_sessions.get(session_id, [])
    
    if len(existing_history) == 0:
        # First turn -> Deep Research Agent
        background_tasks.add_task(
            run_deep_research_task,
            task_id,
            session_id,
            request.message,
            context_str
        )
    else:
        # Follow-up -> Fast Gemini with Search
        background_tasks.add_task(
            run_fast_chat_task,
            task_id,
            session_id,
            request.message,
            context_str
        )
    
    return ChatResponse(
        session_id=session_id,
        task_id=task_id,
        status="processing",
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
        error=task.get("error")
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}
