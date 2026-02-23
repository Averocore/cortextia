"""
community_scraper.py — Step 3
Fetches available Tools and Functions from the official Open WebUI Community API.
"""

from __future__ import annotations
import logging
import time
import requests
from typing import List, Optional, Dict, Any
from pathlib import Path

# Add project root to path for schema import
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from owui_index_generator.schema.extension import CommunityExtension

log = logging.getLogger(__name__)

API_URL = "https://api.openwebui.com/api/v1/posts/search"
WEB_URL = "https://openwebui.com"

class CommunityScraper:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": "Cortextia-Index-Generator/1.0",
            "Accept": "application/json",
        })

    def fetch_page(self, ext_type: str, page: int = 1) -> List[CommunityExtension]:
        """
        ext_type: 'tool', 'function', 'model', 'prompt'
        """
        params = {
            "type": ext_type,
            "sort": "top",
            "t": "all",
            "page": page
        }
        
        log.info(f"Fetching {ext_type}s (API) - Page {page} ...")
        try:
            resp = self.session.get(API_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.error(f"  API request failed: {e}")
            return []

        items = data.get("items", [])
        if not items:
            return []

        extensions = []
        for item in items:
            try:
                # Basic info
                slug = item.get("id")
                name = item.get("title", slug)
                author = item.get("user", {}).get("username", "unknown")
                downloads = item.get("downloads", 0)
                
                # Description logic (try specific meta, then general content)
                item_data = item.get("data", {})
                description = None
                subtype = None
                
                if ext_type == "tool":
                    description = item_data.get("tool", {}).get("meta", {}).get("description")
                elif ext_type == "function":
                    func_data = item_data.get("function", {})
                    description = func_data.get("meta", {}).get("description")
                    subtype = func_data.get("type") # 'pipe', 'filter', 'action'
                
                if not description:
                    description = item.get("content")

                # Clean up description (truncate for table safety)
                if description:
                    description = description.strip().split('\n')[0][:200]

                # URLs
                # Most community posts follow /t/ or /f/ depending on type
                prefix = "t" if ext_type == "tool" else "f"
                if ext_type == "model": prefix = "m"
                if ext_type == "prompt": prefix = "p"
                
                install_url = f"{WEB_URL}/{prefix}/{author}/{slug}"

                extensions.append(CommunityExtension(
                    slug=slug,
                    name=name,
                    type=ext_type,
                    subtype=subtype,
                    description=description,
                    author=author,
                    downloads=downloads,
                    install_url=install_url,
                    status="available"
                ))
            except Exception as e:
                log.warning(f"  Failed to parse item {item.get('id')}: {e}")
                continue
                
        return extensions

    def collect_all(self, max_pages: int = 1) -> Dict[str, List[CommunityExtension]]:
        """Collects tools and functions from the community."""
        results = {
            "tools": [],
            "functions": []
        }
        
        for p in range(1, max_pages + 1):
            tools = self.fetch_page("tool", p)
            if not tools: break
            results["tools"].extend(tools)
            time.sleep(0.5)

        for p in range(1, max_pages + 1):
            functions = self.fetch_page("function", p)
            if not functions: break
            results["functions"].extend(functions)
            time.sleep(0.5)

        log.info(f"Total collected: {len(results['tools'])} tools, {len(results['functions'])} functions.")
        return results

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    scraper = CommunityScraper()
    # Test with 1 page
    res = scraper.collect_all(max_pages=1)
    
    print("\nSAMPLE DATA:")
    for t in res["tools"][:2]:
        print(f"  [TOOL] {t.name} by @{t.author} ({t.downloads} downloads)")
    for f in res["functions"][:2]:
        print(f"  [FUNC] {f.name} ({f.subtype}) by @{f.author}")
