import requests

GUVI_API_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"

def send_guvi_callback(session_id: str, data: dict):
    """
    Sends the extracted intelligence to the GUVI Hackathon API.
    Used as a background task to prevent slowing down the chat.
    """
    try:
        # We set a short timeout (2s) so our API doesn't hang if their server is slow
        response = requests.post(GUVI_API_URL, json=data, timeout=2)
        
        if response.status_code == 200:
            print(f"✅ [SUCCESS] Callback sent for Session: {session_id}")
        else:
            print(f"⚠️ [WARNING] GUVI API returned {response.status_code} for {session_id}")
            
    except requests.exceptions.Timeout:
        print(f"❌ [TIMEOUT] GUVI API took too long for {session_id}")
    except Exception as e:
        print(f"❌ [ERROR] Callback failed: {e}")