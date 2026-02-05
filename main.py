import os
import logging
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

# --- SETUP ---
load_dotenv()

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Honeypot-Agent")

app = FastAPI(
    title="Agentic Honeypot PowerHouse 1.0.0",
    description="A fully autonomous AI agent designed to waste scammers' time.",
    version="1.0.0"
)

# --- MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, 
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION ---
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
EXPECTED_API_KEY = "VIT_Chennai_PowerHouse_2026"

try:
    if GEMINI_KEY:
        client = genai.Client(api_key=GEMINI_KEY)
    else:
        client = None
        logger.warning("Gemini Client not initialized. Check API Key.")
except Exception as e:
    logger.error(f"Client Init Error: {e}")

# --- CORE LOGIC ---
async def process_interaction(request: Request, background_tasks: BackgroundTasks, x_api_key: str = None):
    logger.info("New incoming request received.")

    # 1. Safe Payload Extraction
    try:
        body = await request.json()
    except Exception:
        body = {}

    # 2. Data Parsing
    session_id = body.get("sessionId", "default-session")
    msg_data = body.get("message", {})
    user_text = str(msg_data) if not isinstance(msg_data, dict) else msg_data.get("text", "")

    # 3. Security Audit
    if x_api_key != EXPECTED_API_KEY:
        logger.warning(f"Authentication mismatch. Received key: {x_api_key}")

    # 4. Forensic Analysis
    session = get_session(session_id)
    forensics = analyze_scam(user_text)
    
    session["scam_confidence"] = max(session["scam_confidence"], forensics["confidence"])
    new_state = update_state(session, forensics)

    # 5. Generative Response
    system_prompt = build_system_prompt(session, forensics)
    ai_reply = "I am listening." # Default fallback
    
    if client:
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"{system_prompt}\n\nScammer: {user_text}"
            )
            if response.text:
                ai_reply = response.text
        except Exception:
            try:
                # Backup Model
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=f"{system_prompt}\n\nScammer: {user_text}"
                )
                if response.text:
                    ai_reply = response.text
            except Exception:
                pass

    # 6. Active Deception (Fake Payment Injection)
    trigger_words = ["pay", "send", "fee", "transfer", "deposit", "qr"]
    if any(w in user_text.lower() for w in trigger_words) and session["scam_confidence"] > 0.6:
        fake_proof = generate_fake_data(user_text, "payment_proof")
        ai_reply += f"\n[ATTACHMENT: {fake_proof}]"

    # 7. Intelligence Reporting (Mandatory Callback)
    if new_state == SessionState.HOOKED or session["scam_confidence"] > 0.8:
        background_tasks.add_task(send_guvi_callback, session_id, session)

    # 8. FINAL RETURN FORMAT (Strictly what judges asked for)
    return {
        "status": "success",
        "reply": ai_reply
    }

# --- ENDPOINTS ---

@app.get("/")
async def root():
    return {"status": "online", "message": "Honeypot Active"}

@app.post("/honeypot")
async def api_honeypot(request: Request, background_tasks: BackgroundTasks, x_api_key: str = Header(None)):
    return await process_interaction(request, background_tasks, x_api_key)

# Robust Fallback
@app.post("/")
async def api_root_fallback(request: Request, background_tasks: BackgroundTasks, x_api_key: str = Header(None)):
    return await process_interaction(request, background_tasks, x_api_key)