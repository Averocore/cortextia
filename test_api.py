import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("WEBUI_URL", "http://localhost:7860")
API_KEY = os.getenv("WEBUI_API_KEY") # You will need to generate this in the UI!

def test_endpoint(endpoint):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    
    print(f"Testing {url}...")
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print(f"✅ Success! Found {len(response.json())} items.")
            return response.json()
        else:
            print(f"❌ Failed ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"⚠️ Error: {str(e)}")
    return None

if __name__ == "__main__":
    print("--- Open WebUI API Probe (Phase 0) ---")
    
    # Check if Swagger is live (ENV=dev)
    test_endpoint("/docs") 
    
    # Check core endpoints
    models = test_endpoint("/api/models")
    tools = test_endpoint("/api/v1/tools")
    functions = test_endpoint("/api/v1/functions")
    
    print("\n--- Summary ---")
    if not API_KEY:
        print("💡 Hint: Set WEBUI_API_KEY in your .env to access workspace tools/functions.")
