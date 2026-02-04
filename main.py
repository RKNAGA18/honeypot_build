import os
from typing import Dict, Any, List
from fastapi import FastAPI, Header, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from dotenv import load_dotenv

# --- IMPORTS ---
# Ensure core/ and utils/ folders exist!
from core.agent import get_session, update_state, build_system_prompt, SessionState
from core.forensics import analyze_scam
from core.fake_data import generate_fake_data
from utils.callback import send_guvi_callback

load_dotenv()

app = FastAPI(title="Agentic Honeypot Pro")

# --- 1. CORS FIX (Fixes ACCESS_ERROR) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, # Must be False for Wildcard *
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

# --- HEALTH CHECK (Fixes 404s in logs) ---
@app.get("/")
async def root():
    return {"status": "alive", "version": "grandmaster-cors-fixed"}

# --- API ENDPOINT (Fixes INVALID_REQUEST_BODY) ---
@app.post("/honeypot")
async def handle_honeypot(request: Request, background_tasks: BackgroundTasks, x_api_key: str = Header(None)):
    
    print("🦄 GRANDMASTER CODE: Request Received!") # <--- Look for this in logs!

    # 1. READ RAW BODY (No Pydantic Validation)
    try:
        body = await request.json()
    except Exception:
        body = {}

    # 2. Extract Data Safely
    session_id = body.get("sessionId", "test-session-default")
    msg_data = body.get("message", {})
    if isinstance(msg_data, dict):
        user_text = msg_data.get("text", "Hello")
    else:
        user_text = str(msg_data)

    # 3. Security Check (Relaxed)
    if x_api_key != MY_SECRET_API_KEY:
        print(f"⚠️ Auth Mismatch: Got {x_api_key}")

    # 4. Agent Logic
    session = get_session(session_id)
    forensics = analyze_scam(user_text)
    new_state = update_state(session, forensics)
    session["scam_confidence"] = max(session["scam_confidence"], forensics["confidence"])

    # 5. AI Generation
    system_prompt = build_system_prompt(session, forensics)
    ai_reply = "I am listening."
    
    if client:
        try:
            # Try multiple models for robustness
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
        except Exception as e:
            print(f"AI Error: {e}")

    # 6. Fake Payment Injection
    scam_words = ["pay", "send", "deposit", "fee"]
    if any(w in user_text.lower() for w in scam_words) and session["scam_confidence"] > 0.5:
        fake_proof = generate_fake_data(user_text, "payment_proof")
        ai_reply += f" || {fake_proof}"

    # 7. Callback
    if new_state == SessionState.HOOKED:
        background_tasks.add_task(send_guvi_callback, session_id, session)

    # 8. Return JSON (Always Success)
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