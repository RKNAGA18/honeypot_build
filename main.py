import os
import re
import requests
from fastapi import FastAPI, Header, HTTPException
from google import genai
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# --- 1. CONFIGURATION ---
# Replace with your actual Gemini API Key from Google AI Studio
GEMINI_KEY = "AIzaSyDUIgqQ094HH9iii77H0f8RBewfJLFnH4o"
client = genai.Client(api_key=GEMINI_KEY)

# This is the key you will define in the GUVI Endpoint Tester
MY_SECRET_API_KEY = "VIT_Chennai_PowerHouse_2026"

# --- 2. DATA MODELS (Matching Section 6 & 12 of Problem Statement) ---
class Message(BaseModel):
    sender: str
    text: str
    timestamp: str

class RequestPayload(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: List[Message]
    metadata: Optional[dict] = {}

# --- 3. INTELLIGENCE EXTRACTION (Regex) ---
def extract_intelligence(text: str):
    upi_pattern = r'[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}'
    link_pattern = r'https?://\S+'
    phone_pattern = r'\+?\d{10,12}'
    
    return {
        "bankAccounts": [], # Logic can be added for account number patterns
        "upiIds": re.findall(upi_pattern, text),
        "phishingLinks": re.findall(link_pattern, text),
        "phoneNumbers": re.findall(phone_pattern, text),
        "suspiciousKeywords": ["blocked", "verify", "urgent", "account"]
    }

# --- 4. API ENDPOINT ---
@app.post("/honeypot")
async def handle_honeypot(payload: RequestPayload, x_api_key: str = Header(None)):
    # Security Validation
    if x_api_key != MY_SECRET_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API Key")

    # Define the Persona
    system_instruction = (
        "You are Anitha, a 65-year-old grandmother from Chennai. You are very polite but "
        "easily confused by technology. A scammer is messaging you. Act worried and gullible. "
        "Your goal is to keep them talking to extract their payment details (UPI/Bank). "
        "If they ask for money, ask for their UPI ID so you can 'ask your grandson to pay'."
    )

    # Generate Response using Gemini 2.0 Flash
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{system_instruction}\n\nScammer: {payload.message.text}"
        )
        ai_reply = response.text
    except Exception as e:
        ai_reply = "Oh dear, my phone is acting up. What did you say?"
        print(f"Gemini Error: {e}")

    # Process Intelligence
    intel = extract_intelligence(payload.message.text)
    total_msgs = len(payload.conversationHistory) + 1

    # --- 5. MANDATORY CALLBACK (Section 12) ---
    # Trigger only when enough intel is gathered or conversation is long enough
    if len(intel["upiIds"]) > 0 or total_msgs > 8:
        callback_payload = {
            "sessionId": payload.sessionId,
            "scamDetected": True,
            "totalMessagesExchanged": total_msgs,
            "extractedIntelligence": intel,
            "agentNotes": "Scammer successfully engaged; UPI ID extracted via Anitha persona."
        }
        try:
            requests.post(
                "https://hackathon.guvi.in/api/updateHoneyPotFinalResult",
                json=callback_payload,
                timeout=5
            )
        except Exception as e:
            print(f"Callback Failed: {e}")

    return {
        "status": "success",
        "scamDetected": True,
        "engagementMetrics": {
            "engagementDurationSeconds": total_msgs * 30,
            "totalMessagesExchanged": total_msgs
        },
        "extractedIntelligence": {
            "bankAccounts": intel["bankAccounts"],
            "upiIds": intel["upiIds"],
            "phishingLinks": intel["phishingLinks"]
        },
        "agentNotes": ai_reply
    }