import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("WEBUI_URL", "http://localhost:7860").rstrip("/")
API_KEY = os.getenv("WEBUI_API_KEY", "")

ENDPOINTS = {
    "config":    "/api/config",
    "models":    "/api/models",
    "tools":     "/api/v1/tools/",
    "functions": "/api/v1/functions/",
    "prompts":   "/api/v1/prompts/",
    "knowledge": "/api/v1/knowledge/",
}

os.makedirs("samples", exist_ok=True)

def test_endpoint(name, path):
    url = f"{BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    print(f"\nTesting {name}: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                count = len(data) if isinstance(data, list) else "N/A (object)"
                print(f"  ✅ Success! Items: {count}")
                with open(f"samples/{name}.json", "w") as f:
                    json.dump(data, f, indent=2)
                print(f"  💾 Saved to samples/{name}.json")
                return data
            except Exception:
                print(f"  ⚠️ Response is not JSON. Body: {response.text[:200]}")
        else:
            print(f"  ❌ Failed: {response.text[:200]}")
    except Exception as e:
        print(f"  ⚠️ Error: {e}")
    return None

if __name__ == "__main__":
    print("=" * 50)
    print("Open WebUI API Probe — Step 1D")
    print(f"Instance: {BASE_URL}")
    print(f"Auth:     {'✅ Key loaded' if API_KEY else '❌ No WEBUI_API_KEY in .env'}")
    print("=" * 50)

    results = {}
    for name, path in ENDPOINTS.items():
        results[name] = test_endpoint(name, path)

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for name, data in results.items():
        if data is None:
            print(f"  ❌ {name}: failed")
        elif isinstance(data, list):
            print(f"  ✅ {name}: {len(data)} items")
        else:
            print(f"  ✅ {name}: returned object")
    print("\nSample JSON files saved to: ./samples/")
