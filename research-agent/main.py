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
- Do NOT create a separate bibliography or reference list at the end.
- Distinguish factual vs speculative.
- Be skeptical, precise, and high-signal. Do not be encouraging by default.

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
- Include 1-2 relevant links when making specific claims
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
        You are a Sequoia Capital partner. Write a tactical, scannable guide.
        Topic: "{request.question}"

        CRITICAL CONSTRAINTS:
        • **Length:** 150-180 words MAXIMUM. Be ruthlessly concise.
        • **Style:** Direct. No fluff. Every word must add value.
        • **Format:** Scannable with clear visual breaks

        REQUIRED STRUCTURE:

        ## Core Principle
        One sentence. The essence.

        **Why Founders Fail**
        One sentence only. The critical mistake.

        **How to Execute**
        - **Action 1:** One tactical step (max 8 words)
        - **Action 2:** One tactical step (max 8 words)
        - **Action 3:** One tactical step (max 8 words)

        **Key Signal**
        One sentence. What to measure.

        **Example**
        One company, one outcome. Max 15 words.

        FORMATTING RULES:
        - Bold the first word of each bullet
        - Keep bullets under 10 words each
        - ONE example only, ultra-brief
        - Add blank lines between sections
        - No explanatory text, just facts

        OUTPUT:
        Return ONLY markdown. Start with ## Core Principle.
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
