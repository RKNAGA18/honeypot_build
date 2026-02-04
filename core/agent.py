from typing import Dict
from .personas import get_random_persona
import random

# In-Memory Session Store
session_store: Dict[str, dict] = {}

class SessionState:
    INIT = "INIT"           # First contact
    ENGAGING = "ENGAGING"   # Asking details
    HOOKED = "HOOKED"       # Scammer asked for money (We are ready to pay)
    TRAPPED = "TRAPPED"     # We sent fake proof (Scammer is confused)
    STALLING = "STALLING"   # We are wasting time (Battery low, wrong OTPs)
    EXIT = "EXIT"           # Reveal or End

def get_session(session_id: str):
    if session_id not in session_store:
        session_store[session_id] = {
            "state": SessionState.INIT,
            "persona": get_random_persona(),
            "messages_count": 0,
            "scam_confidence": 0.0,
            "extracted_data": {"upi": [], "bank": [], "phone": []},
            "callback_sent": False,
            "last_action": None,
            "otp_attempts": 0  # Tracks how many wrong OTPs we sent
        }
    return session_store[session_id]

def update_state(session, forensics_result):
    """
    Determines the next state based on the scammer's input.
    """
    current_state = session["state"]
    new_state = current_state
    
    # Check if the scammer is demanding money right now
    has_money_talk = (
        forensics_result["extracted"]["amount"] or 
        "Financial Demand" in forensics_result["tactics"]
    )

    # --- STATE TRANSITION LOGIC ---

    # 1. Fast Track: If they ask for money immediately, JUMP to HOOKED
    # This fixes the "passive" issue where it ignored the first money request.
    if has_money_talk and session["scam_confidence"] > 0.6:
        new_state = SessionState.HOOKED
        
    # 2. Standard Progression (Init -> Engaging)
    elif current_state == SessionState.INIT and session["scam_confidence"] > 0.6:
        new_state = SessionState.ENGAGING
        
    # 3. Engaging -> Hooked (If they mention money later)
    elif current_state == SessionState.ENGAGING and has_money_talk:
        new_state = SessionState.HOOKED
        
    # 4. Hooked -> Trapped (Triggered manually in main.py after sending fake proof)
    elif current_state == SessionState.HOOKED and session.get("last_action") == "payment_proof":
        new_state = SessionState.TRAPPED
        
    # 5. Trapped -> Stalling (After they get confused, we start wasting time)
    elif current_state == SessionState.TRAPPED and session["messages_count"] > 6:
        new_state = SessionState.STALLING
        
    session["state"] = new_state
    return new_state

def build_system_prompt(session, forensics_result):
    persona = session["persona"]
    state = session["state"]
    
    # Base Personality
    prompt = (
        f"You are {persona['name']}, {persona['age']} years old. "
        f"Personality: {persona['tone']}. Flaw: {persona['flaw']}. "
        f"Current State: {state}. "
        f"Scammer Tactics detected: {forensics_result['tactics']}. "
        "INSTRUCTIONS: "
        "1. Keep responses short (WhatsApp/SMS style). "
        "2. Use '||' to separate multiple messages. "
        "3. Make intentional typos consistent with your age. "
    )
    
    # State-Specific Instructions
    if state == SessionState.HOOKED:
        prompt += " ACTION: Pretend you are eager to pay or send the details. Ask if you should use UPI."
        
    elif state == SessionState.TRAPPED:
        prompt += (
            " ACTION: Act confused. You sent the money (fake proof was sent). "
            "Ask why they haven't received it. Blame the server."
        )
    
    elif state == SessionState.STALLING:
        prompt += (
            " ACTION: MAXIMUM ANNOYANCE. "
            "If they ask for OTP, give a wrong number. "
            "Say 'Battery low', 'Grandson calling', or 'Network bad'. "
            "DO NOT admit you are an AI. Just waste their time."
        )
        
    return prompt