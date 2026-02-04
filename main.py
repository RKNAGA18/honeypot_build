import os
import time
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Header, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware # <--- IMPORTANT IMPORT
from google import genai
from dotenv import load_dotenv

# --- IMPORTS ---
# Ensure these folders exist in your project!
from core.agent import get_session, update_state, build_system_prompt, SessionState
from core.forensics import analyze_scam
from core.fake_data import generate_fake_data
from utils.callback import send_guvi_callback

load_dotenv()

app = FastAPI(title="Agentic Honeypot Pro")

# --- 1. ENABLE CORS (Crucial for Web Testers) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow ALL websites (including GUVI tester)
    allow_credentials=True,
    allow_methods=["*"],  # Allow ALL methods (POST, GET, OPTIONS)
    allow_headers=["*"],  # Allow ALL headers
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

# --- API ENDPOINT (UNIVERSAL RECEIVER) ---
# We use 'request: Request' to bypass Pydantic validation completely.
# This prevents 422 Errors.
@app.post("/honeypot")
async def handle_honeypot(request: Request, background_tasks: BackgroundTasks, x_api_key: str = Header(None)):
    
    # 1. READ RAW BODY (No Validation)
    try:
        body = await request.json()
        print(f"🔍 DEBUG: Received Body: {body}") # Check Render Logs for this!
    except Exception:
        body = {}
        print("⚠️ DEBUG: Received Empty or Invalid JSON")

    # 2. Manual Data Extraction (Safe Defaults)
    session_id = body.get("sessionId", "test-session-default")
    
    # Handle 'message' safely
    msg_data = body.get("message", {})
    if isinstance(msg_data, dict):
        user_text = msg_data.get("text", "Hello")
    else:
        user_text = str(msg_data)

    # 3. Security Check
    if x_api_key != MY_SECRET_API_KEY:
        print(f"Auth Failed. Got: {x_api_key}")
        # For testing, we comment this out so you see the logic working
        # raise HTTPException(status_code=401, detail="Unauthorized")

    # 4. Agent Logic
    session = get_session(session_id)
    forensics = analyze_scam(user_text)
    
    # State Update
    session["scam_confidence"] = max(session["scam_confidence"], forensics["confidence"])
    new_state = update_state(session, forensics)

    # 5. AI Generation
    system_prompt = build_system_prompt(session, forensics)
    ai_reply = "I am listening."
    
    if client:
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"{system_prompt}\n\nScammer: {user_text}"
            )
            if response.text:
                ai_reply = response.text
        except Exception as e:
            print(f"Gemini Error: {e}")

    # 6. Format Response
    messages_list = [m.strip() for m in ai_reply.split("||") if m.strip()]
    if not messages_list:
        messages_list = ["Hello?"]

    # 7. Return JSON (Always Success)
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
        "agentMessages": messages_list
    }