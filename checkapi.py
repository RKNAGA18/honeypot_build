from google import genai

# 🚨 PASTE YOUR AIzaSy... KEY DIRECTLY HERE
# Do not leave it empty. Paste it inside the quotes!
API_KEY = "your api" 

print(f"Checking models for Key: {API_KEY[:10]}...")

client = genai.Client(api_key=API_KEY)

try:
    print("\n--- AVAILABLE MODELS ---")
    for m in client.models.list():
        # Clean up the name to show just the ID you need
        clean_name = m.name.replace("models/", "")
        print(f"✅ {clean_name}")
    print("------------------------\n")
            
except Exception as e:
    print(f"❌ Error: {e}")
