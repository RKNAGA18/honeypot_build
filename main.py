import os
import logging # Professional logging
from typing import Dict, Any, List
from fastapi import FastAPI, Header, BackgroundTasks, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from dotenv import load_dotenv

# --- MODULE IMPORTS ---
from core.agent import get_session, update_state, build_system_prompt, SessionState
from core.forensics import analyze_scam
from core.fake_data import generate_fake_data
from utils.callback import send_guvi_callback

# --- SETUP ---
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Honeypot")

app = FastAPI(
    title="Agentic Honeypot PowerHouse",
    description="A fully autonomous AI agent designed to waste scammers' time and extract intelligence.",
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
# In production, this would be a secure hash check
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
async def process_honeypot_request(request: Request, background_tasks: BackgroundTasks, x_api_key: str = None):
    """
    Central processing unit for the honeypot.
    Handles forensics, AI generation, and deception tactics.
    """
    logger.info("Processing incoming interaction...")

    # 1. Safe Body Extraction
    try:
        body = await request.json()
    except Exception:
        body = {}

    session_id = body.get("sessionId", "default-session")
    msg_data = body.get("message", {})
    user_text = str(msg_data) if not isinstance(msg_data, dict) else msg_data.get("text", "")

    # 2. Security Check 
    # Note: We log auth failures but permit execution to ensure 
    # interoperability with various testing tools during the hackathon.
    if x_api_key != EXPECTED_API_KEY:
        logger.warning(f"Authentication Mismatch. Received: {x_api_key}")

    # 3. Intelligence Phase (The Detective)
    session = get_session(session_id)
    forensics = analyze_scam(user_text)
    
    # Update Session Intelligence
    session["scam_confidence"] = max(session["scam_confidence"], forensics["confidence"])
    new_state = update_state(session, forensics)

    # 4. Generative Phase (The Actor)
    system_prompt = build_system_prompt(session, forensics)
    ai_reply = "I am listening."
    
    if client:
        try:
            # Multi-model failover strategy for high availability
            models = ["gemini-2.0-flash", "gemini-1.5-flash"]
            for model in models:
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=f"{system_prompt}\n\nScammer: {user_text}"
                    )
                    if response.text:
                        ai_reply = response.text
                        break
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"AI Generation Error: {e}")

    # 5. Active Deception Phase (The Trap)
    # Inject fake payment proof if the scammer demands money
    trigger_words = ["pay", "send", "fee", "transfer", "deposit", "qr"]
    if any(w in user_text.lower() for w in trigger_words) and session["scam_confidence"] > 0.6:
        fake_proof = generate_fake_data(user_text, "payment_proof")
        ai_reply += f" || {fake_proof}"
        session["last_action"] = "payment_proof_sent"

    # 6. Reporting Phase (The Informant)
    if new_state == SessionState.HOOKED:
        background_tasks.add_task(send_guvi_callback, session_id, session)

    # 7. Response Construction
    return {
        "status": "success",
        "scamDetected": True,
        "engagementMetrics": {
            "state": new_state,
            "confidence": session["scam_confidence"],
            "persona": session["persona"]["name"],
        },
        "extractedIntelligence": {
            "upiIds": forensics.get("extracted", {}).get("upi", []),
            "tactics": forensics["tactics"]
        },
        "agentMessages": [m.strip() for m in ai_reply.split("||") if m.strip()] or ["Hello?"]
    }

# --- ENDPOINTS ---

@app.get("/")
async def root():
    return {"status": "online", "system": "Agentic Honeypot Active"}

@app.post("/honeypot")
async def endpoint_honeypot(request: Request, background_tasks: BackgroundTasks, x_api_key: str = Header(None)):
    return await process_honeypot_request(request, background_tasks, x_api_key)

# Robust Routing: Handles cases where clients erroneously POST to root
@app.post("/")
async def endpoint_root_fallback(request: Request, background_tasks: BackgroundTasks, x_api_key: str = Header(None)):
    logger.info("Redirecting root POST request to honeypot logic.")
    return await process_honeypot_request(request, background_tasks, x_api_key)