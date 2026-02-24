"""
knowledge_sync.py
Uploads or replaces the OWUI_INDEX.md file in an Open WebUI Knowledge collection.

Workflow:
  1. Upload the .md file via POST /api/v1/files/
  2. Create or update a Knowledge collection via the Knowledge API
  3. Attach the uploaded file to that collection
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

class KnowledgeSync:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
        }
        self.collection_name = "OWUI Extension Index"
        self.collection_description = (
            "Auto-generated catalog of all installed and available "
            "Open WebUI extensions — tools, functions, models, prompts, "
            "pipelines, and MCP servers."
        )

    def upload_file(self, filepath: str) -> dict:
        """Upload a file and return the file metadata."""
        url = f"{self.base_url}/api/v1/files/"
        filename = Path(filepath).name

        try:
            with open(filepath, "rb") as f:
                resp = requests.post(
                    url,
                    headers=self.headers,
                    files={"file": (filename, f, "text/markdown")},
                )
            resp.raise_for_status()
            file_data = resp.json()
            print(f"  ✅ File uploaded: {file_data.get('id')} ({filename})")
            return file_data
        except Exception as e:
            print(f"  ❌ Failed to upload file: {e}")
            raise

    def find_existing_collection(self) -> dict | None:
        """Check if our Knowledge collection already exists."""
        url = f"{self.base_url}/api/v1/knowledge/"
        try:
            resp = requests.get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            
            # Open WebUI API version consistency check
            collections = data.get("items", data) if isinstance(data, dict) else data

            for col in collections:
                if isinstance(col, dict) and col.get("name") == self.collection_name:
                    return col
            return None
        except Exception as e:
            print(f"  ❌ Failed to fetch collections: {e}")
            raise

    def create_collection(self, file_id: str) -> dict:
        """Create a new Knowledge collection with the file attached."""
        url = f"{self.base_url}/api/v1/knowledge/create"
        payload = {
            "name": self.collection_name,
            "description": self.collection_description,
            "data": {"file_ids": [file_id]},
        }
        try:
            resp = requests.post(url, headers=self.headers, json=payload)
            resp.raise_for_status()
            col = resp.json()
            print(f"  ✅ Collection created: {col.get('id')}")
            return col
        except Exception as e:
            print(f"  ❌ Failed to create collection: {e}")
            raise

    def update_collection(self, collection_id: str, file_id: str) -> dict:
        """
        Replace the file in an existing collection.
        Steps:
          1. Remove old files from the collection
          2. Add the new file
        """
        # Add new file to collection
        url = f"{self.base_url}/api/v1/knowledge/{collection_id}/file/add"
        try:
            resp = requests.post(
                url,
                headers=self.headers,
                json={"file_id": file_id},
            )
            resp.raise_for_status()
            print(f"  ✅ Collection updated: {collection_id}")
            return resp.json()
        except Exception as e:
            print(f"  ❌ Failed to update collection: {e}")
            raise

    def remove_old_files(self, collection_id: str, keep_file_id: str):
        """Remove all files from collection except the one we just uploaded."""
        url = f"{self.base_url}/api/v1/knowledge/{collection_id}"
        try:
            resp = requests.get(url, headers=self.headers)
            resp.raise_for_status()
            col = resp.json()

            # Handle different response formats for single collection
            data = col.get("data", col) if isinstance(col, dict) else {}
            existing_files = data.get("file_ids", []) if isinstance(data, dict) else []
            
            for fid in existing_files:
                if fid != keep_file_id:
                    remove_url = (
                        f"{self.base_url}/api/v1/knowledge/{collection_id}"
                        f"/file/remove"
                    )
                    requests.post(
                        remove_url,
                        headers=self.headers,
                        json={"file_id": fid},
                    )
                    print(f"  🗑️  Removed old file: {fid}")
        except Exception as e:
            print(f"  ⚠️ Warning: Failed to remove some old files: {e}")

    def sync(self, filepath: str):
        """Main entry point: upload file and sync to Knowledge."""
        print(f"📤 Syncing {filepath} to Knowledge...")

        # 1. Upload the file
        file_data = self.upload_file(filepath)
        file_id = file_data["id"]

        # 2. Find or create the collection
        existing = self.find_existing_collection()

        if existing:
            col_id = existing["id"]
            print(f"  📂 Found existing collection: {col_id}")
            self.update_collection(col_id, file_id)
            self.remove_old_files(col_id, file_id)
        else:
            print("  📂 No existing collection found, creating new...")
            self.create_collection(file_id)

        print("✅ Knowledge sync complete.")
        return file_id


def main():
    base_url = os.getenv("OWUI_BASE_URL") or os.getenv("WEBUI_URL") or "http://localhost:7860"
    api_key = os.getenv("WEBUI_API_KEY", "")

    if not api_key:
        print("❌ WEBUI_API_KEY not set in environment or .env file.")
        sys.exit(1)

    index_path = Path(__file__).parent.parent.parent / "data" / "OWUI_INDEX.md"
    if not index_path.exists():
        print(f"❌ Index file not found at {index_path}")
        print("   Run generate_index.py first.")
        sys.exit(1)

    syncer = KnowledgeSync(base_url, api_key)
    try:
        syncer.sync(str(index_path))
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
