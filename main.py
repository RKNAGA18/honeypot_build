import os
from typing import Dict, Any, List
from fastapi import FastAPI, Header, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from dotenv import load_dotenv

# --- IMPORTS ---
from core.agent import get_session, update_state, build_system_prompt, SessionState
from core.forensics import analyze_scam
from core.fake_data import generate_fake_data
from utils.callback import send_guvi_callback

load_dotenv()

app = FastAPI(title="Agentic Honeypot Pro")

# --- 1. CORS FIX (Crucial for Tester) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, 
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION ---
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
MY_SECRET_API_KEY = "VIT_Chennai_PowerHouse_2026"

try:
    if GEMINI_KEY:
        client = genai.Client(api_key=GEMINI_KEY)
    else:
        client = None
except Exception as e:
    print(f"Client Init Error: {e}")

# --- 2. SHARED LOGIC (The Brain) ---
# We move the logic here so both endpoints can use it.
async def process_honeypot_request(request: Request, background_tasks: BackgroundTasks, x_api_key: str = None):
    print("🦄 REQUEST RECEIVED: Processing...") 

    # Read Body Safely
    try:
        body = await request.json()
    except Exception:
        body = {}

    # Extract Data
    session_id = body.get("sessionId", "test-session-default")
    msg_data = body.get("message", {})
    user_text = str(msg_data) if not isinstance(msg_data, dict) else msg_data.get("text", "Hello")

    # Security Warning (Log only)
    if x_api_key != MY_SECRET_API_KEY:
        print(f"⚠️ Auth Mismatch: Got {x_api_key}")

    # Core Logic
    session = get_session(session_id)
    forensics = analyze_scam(user_text)
    new_state = update_state(session, forensics)
    session["scam_confidence"] = max(session["scam_confidence"], forensics["confidence"])

    # AI Response
    system_prompt = build_system_prompt(session, forensics)
    ai_reply = "I am listening."
    
    if client:
        try:
            for model in ["gemini-2.0-flash", "gemini-1.5-flash"]:
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=f"{system_prompt}\n\nScammer: {user_text}"
                    )
                    if response.text:
                        ai_reply = response.text
                        break
                except:
                    continue
        except Exception:
            pass

    # Fake Payment Trigger
    if any(w in user_text.lower() for w in ["pay", "send", "fee"]) and session["scam_confidence"] > 0.5:
        fake_proof = generate_fake_data(user_text, "payment_proof")
        ai_reply += f" || {fake_proof}"

    # Callback
    if new_state == SessionState.HOOKED:
        background_tasks.add_task(send_guvi_callback, session_id, session)

    return {
        "status": "success",
        "scamDetected": True,
        "engagementMetrics": {
            "state": new_state,
            "confidence": session["scam_confidence"],
            "persona": session["persona"]["name"],
        },
        "extractedIntelligence": {
            "upiIds": [],
            "tactics": forensics["tactics"]
        },
        "agentMessages": [m.strip() for m in ai_reply.split("||") if m.strip()] or ["Hello?"]
    }

# --- 3. ENDPOINTS ---

# The Correct Endpoint
@app.post("/honeypot")
async def endpoint_honeypot(request: Request, background_tasks: BackgroundTasks, x_api_key: str = Header(None)):
    return await process_honeypot_request(request, background_tasks, x_api_key)

# The "Mistake" Catcher (Fixes 405 Error)
# If you accidentally use the home URL, this catches it and runs the honeypot anyway.
@app.post("/")
async def endpoint_root_post(request: Request, background_tasks: BackgroundTasks, x_api_key: str = Header(None)):
    print("⚠️ User used wrong URL (Root), redirecting logic...")
    return await process_honeypot_request(request, background_tasks, x_api_key)

@app.get("/")
async def root():
    return {"status": "alive", "message": "Use /honeypot endpoint for POST requests"}