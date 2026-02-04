import re

def analyze_scam(text: str):
    text_lower = text.lower()
    
    # 1. Regex Patterns (The "Eyes")
    patterns = {
        "upi": r'[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}',
        "phone": r'(?:\+91[\-\s]?)?[6-9]\d{9}',
        "amount": r'(?:rs\.?|inr)\s*[\d,]+',
        "otp_request": r'\b(otp|code|pin|password)\b'
    }
    
    extracted = {}
    for key, pattern in patterns.items():
        extracted[key] = re.findall(pattern, text, re.IGNORECASE)

    # 2. Tactics Detection (The "Brain")
    tactics = []
    confidence = 0.1 # Base confidence
    
    # Tactic: Urgency
    if any(w in text_lower for w in ["urgent", "immediately", "lapse", "block", "24 hours", "expires"]):
        tactics.append("Urgency")
        confidence += 0.3
        
    # Tactic: Greed (Lottery/Prize)
    if any(w in text_lower for w in ["winner", "lottery", "prize", "congratulations", "cashback", "refund", "credit"]):
        tactics.append("Greed")
        confidence += 0.4
        
    # Tactic: Fear (Authority/Legal)
    if any(w in text_lower for w in ["police", "cbi", "court", "arrest", "illegal", "suspend", "cyber"]):
        tactics.append("Fear")
        confidence += 0.5
        
    # Tactic: Financial Demand (The Aggressive Trigger)
    # If they ask for money, it is almost certainly a scam.
    if any(w in text_lower for w in ["pay", "fee", "charges", "deposit", "transfer", "registration", "tax"]):
        tactics.append("Financial Demand")
        confidence += 0.5 

    # Tactic: Credential Harvesting
    if extracted.get("otp_request"):
        tactics.append("Credential Harvesting")
        confidence += 0.4
        
    # 3. Technical Verification
    # If we found a UPI ID or an Amount pattern, boost confidence.
    if extracted.get("upi") or extracted.get("amount"):
        confidence += 0.3

    return {
        "extracted": extracted,
        "tactics": tactics,
        "confidence": min(confidence, 1.0)
    }