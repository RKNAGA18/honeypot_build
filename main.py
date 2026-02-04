import os
import time
import asyncio
from typing import List, Optional
from fastapi import FastAPI, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv

# --- IMPORT MODULES FROM YOUR NEW FOLDERS ---
from core.agent import get_session, update_state, build_system_prompt, SessionState
from core.forensics import analyze_scam
from core.fake_data import generate_fake_data
from utils.callback import send_guvi_callback

# 1. FORCE LOAD SECRETS (Fixes the VS Code warning)
load_dotenv()

app = FastAPI(title="Agentic Honeypot PowerHouse")

# --- CONFIGURATION ---
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
MY_SECRET_API_KEY = "VIT_Chennai_PowerHouse_2026"

# Initialize Gemini Client
try:
    if GEMINI_KEY:
        client = genai.Client(api_key=GEMINI_KEY)
        print("✅ Gemini Client Initialized successfully.")
    else:
        print("⚠️ CRITICAL ERROR: GEMINI_API_KEY not found in .env file!")
        client = None
except Exception as e:
    print(f"Client Init Error: {e}")

# --- DATA MODELS ---
class Message(BaseModel):
    sender: str
    text: str
    timestamp: str

class RequestPayload(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: List[Message]
    metadata: Optional[dict] = {}

# --- API ENDPOINT ---
@app.post("/honeypot")
async def handle_honeypot(payload: RequestPayload, background_tasks: BackgroundTasks, x_api_key: str = Header(None)):
    
    # 1. Security Check
    if x_api_key != MY_SECRET_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized Access")

    # 2. Session Management (The Brain)
    session = get_session(payload.sessionId)
    session["messages_count"] += 1
    
    # 3. Forensics Analysis (The Detective)
    forensics = analyze_scam(payload.message.text)
    
    # Update Session Intelligence
    session["scam_confidence"] = max(session["scam_confidence"], forensics["confidence"])
    session["extracted_data"]["upi"].extend(forensics["extracted"]["upi"])
    
    # 4. State Machine Update
    new_state = update_state(session, forensics)
    
    # 5. Gatekeeper: Ignore Non-Scammers
    if session["scam_confidence"] < 0.4:
        return {
            "status": "ignored", 
            "scamDetected": False, 
            "agentMessages": ["Who is this?", "I think you have the wrong number."]
        }

    # 6. AI Generation (The Actor)
    system_prompt = build_system_prompt(session, forensics)
    ai_reply = ""
    
    # Multi-Model Failover (Rate Limit Protection)
    models_to_try = ["gemini-2.5-flash", "gemini-exp-1206", "gemini-2.0-flash"]
    
    for model in models_to_try:
        try:
            response = client.models.generate_content(
                model=model,
                contents=f"{system_prompt}\n\nScammer: {payload.message.text}"
            )
            ai_reply = response.text
            break # Success!
        except Exception as e:
            if "429" in str(e): 
                time.sleep(1) # Wait a bit if rate limited
                continue
            else: 
                print(f"Model Error: {e}")
                break
            
    if not ai_reply: 
        ai_reply = "Network bad... || Hello? Can you hear me?"

    # 7. Active Deception Injection (The Nuclear Option)
    # ... inside handle_honeypot function ...

    # 7. Active Deception Injection (Updated)
    scam_trigger_words = ["pay", "send", "transfer", "deposit", "scan"]
    otp_trigger_words = ["otp", "code", "pin", "password"]
    
    # A. Fake Payment Trigger
    if new_state == SessionState.HOOKED and any(w in payload.message.text.lower() for w in scam_trigger_words):
        fake_proof = generate_fake_data(payload.message.text, "payment_proof")
        ai_reply += f" {fake_proof}"
        session["last_action"] = "payment_proof"

    # B. Fake OTP Trigger (The Loop)
    elif any(w in payload.message.text.lower() for w in otp_trigger_words):
        # Only give OTP if we are deep in conversation
        if session["messages_count"] > 2:
            fake_otp = generate_fake_data(payload.message.text, "otp")
            ai_reply += f" {fake_otp}"
            session["otp_attempts"] += 1
            session["last_action"] = "fake_otp"

    # 8. Format Response
    messages_list = [m.strip() for m in ai_reply.split("||") if m.strip()]

    # 9. Callback Logic (The Scoreboard Update)
    should_send_callback = (
        session["scam_confidence"] > 0.8 and 
        not session["callback_sent"] and 
        (new_state == SessionState.TRAPPED or session["messages_count"] > 5)
    )

    if should_send_callback:
        callback_data = {
            "sessionId": payload.sessionId,
            "scamDetected": True,
            "totalMessagesExchanged": session["messages_count"],
            "extractedIntelligence": {
                "upiIds": list(set(session["extracted_data"]["upi"])),
                "tactics": forensics["tactics"],
                "confidenceScore": session["scam_confidence"]
            },
            "agentNotes": f"Persona {session['persona']['name']} engaged. Final State: {new_state}. Fake Data Injected: {session.get('last_action') == 'payment_proof'}"
        }
        # Send in background to keep API fast
        background_tasks.add_task(send_guvi_callback, payload.sessionId, callback_data)
        session["callback_sent"] = True

    # 10. Return JSON
    return {
        "status": "success",
        "scamDetected": True,
        "engagementMetrics": {
            "state": new_state,
            "confidence": session["scam_confidence"],
            "persona": session["persona"]["name"],
            "mood": session["persona"]["tone"]
        },
        "extractedIntelligence": {
            "upiIds": list(set(session["extracted_data"]["upi"])),
            "tactics": forensics["tactics"]
        },
        "agentMessages": messages_list
    }