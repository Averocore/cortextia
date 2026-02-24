"""
title: Index Regenerator
author: Cortextia
author_url: https://github.com/Averocore/cortextia
version: 1.0.0
description: Regenerates the OWUI Extension Index by re-querying local APIs and the community catalog. Run this after installing or removing extensions.
required_open_webui_version: 0.4.0
"""

import json
import os
import requests
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        owui_base_url: str = Field(
            default="http://localhost:7860",
            description="Base URL of the Open WebUI instance (internal)",
        )
        api_key: str = Field(
            default="",
            description="Open WebUI API key (Bearer token). Fallback: WEBUI_API_KEY env var.",
        )
        output_dir: str = Field(
            default="/app/backend/data",
            description="Directory where index files are written",
        )
        community_pages: int = Field(
            default=1,
            description="Number of pages to fetch from the community catalog (per type)",
        )
        include_community: bool = Field(
            default=True,
            description="Whether to include community catalog in regeneration",
        )
        compact_json: bool = Field(
            default=False,
            description="Use compact JSON formatting to reduce file size",
        )
        description_limit: int = Field(
            default=500,
            description="Max characters for community descriptions",
        )

    def __init__(self):
        self.valves = self.Valves()

    def _get_api_key(self) -> str:
        """Get API key from Valves or environment variable."""
        return self.valves.api_key or os.getenv("WEBUI_API_KEY", "")

    def _fetch_local(self, session: requests.Session, base: str, headers: dict, key: str, path: str) -> tuple[str, list]:
        """Fetch a single local endpoint."""
        try:
            resp = session.get(f"{base}{path}", headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", data) if isinstance(data, dict) else data
            return key, items if isinstance(items, list) else []
        except Exception as e:
            return key, [f"Error: {str(e)}"]

    def _fetch_community(self, session: requests.Session, ext_type: str, page: int) -> list[dict]:
        """Fetch community items with retry logic."""
        # REG-02: Ensure literal &type=
        api_url = f"https://api.openwebui.com/api/v1/posts/search?page={page}&type={ext_type[:-1]}"
        
        # REG-07: Retry/backoff
        for attempt in range(3):
            try:
                resp = session.get(api_url, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                return data.get("items", [])
            except Exception:
                if attempt == 2:
                    return []
                time.sleep(2 ** attempt)
        return []

    def _atomic_write(self, path: str, content: str):
        """REG-04: Atomic write using temp file."""
        temp_path = f"{path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, path)

    def regenerate_index(self) -> str:
        """
        Regenerate the Open WebUI Extension Index.
        """
        base = self.valves.owui_base_url.rstrip("/")
        api_key = self._get_api_key()
        out_dir = self.valves.output_dir

        # REG-03: Env fallback verification
        if not api_key:
            return (
                "❌ API key not found. Set the `api_key` Valve or `WEBUI_API_KEY` environment variable."
            )

        headers = {"Authorization": f"Bearer {api_key}"}
        report = ["## 🔄 Index Regeneration Report\n"]
        report.append(f"**Started:** {datetime.now(timezone.utc).isoformat()}\n")

        index_data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "instance_url": base,
        }

        # REG-08: Session + Connection Reuse
        session = requests.Session()

        # --- Local API Collection (Concurrency) ---
        endpoints = {
            "models": "/api/models",
            "tools_installed": "/api/v1/tools",
            "functions_installed": "/api/v1/functions",
            "prompts": "/api/prompts",
            "knowledge_bases": "/api/v1/knowledge",
        }

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(self._fetch_local, session, base, headers, k, v)
                for k, v in endpoints.items()
            ]
            for future in futures:
                key, items = future.result()
                if items and isinstance(items[0], str) and items[0].startswith("Error:"):
                    report.append(f"- ❌ `{key}`: {items[0]}")
                    index_data[key] = []
                else:
                    index_data[key] = items
                    report.append(f"- ✅ `{key}`: {len(items)} items")

        # --- Community Catalog ---
        if self.valves.include_community:
            report.append("\n**Community catalog:**")
            for ext_type in ["tools", "functions"]:
                # REG-06: Deduplication
                seen_ids = set()
                items_collected = []
                
                for page in range(1, self.valves.community_pages + 1):
                    raw_items = self._fetch_community(session, ext_type, page)
                    for item in raw_items:
                        slug = item.get("id")
                        if not slug or slug in seen_ids:
                            continue
                        seen_ids.add(slug)

                        author = item.get("user", {}).get("username", "unknown")
                        
                        # REG-05: Sanitize Description
                        desc = item.get("content", "")
                        desc = " ".join(desc.split()).strip()
                        if len(desc) > self.valves.description_limit:
                            desc = desc[: self.valves.description_limit] + "..."

                        # REG-01: Correct URL Prefixes
                        prefix = "t" if ext_type == "tools" else "f"
                        
                        items_collected.append({
                            "slug": slug,
                            "name": item.get("title", slug),
                            "type": ext_type[:-1],
                            "description": desc,
                            "author": author,
                            "downloads": item.get("downloads", 0),
                            "install_url": f"https://openwebui.com/{prefix}/{author}/{slug}",
                            "status": "available"
                        })
                
                index_data[f"{ext_type}_available"] = items_collected
                report.append(f"  - ✅ {ext_type.title()}: {len(items_collected)} available")

        # --- Save Outputs ---
        try:
            if not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            
            # REG-09: Compact JSON
            json_kwargs = {"indent": 2} if not self.valves.compact_json else {"separators": (",", ":")}
            json_content = json.dumps(index_data, **json_kwargs, ensure_ascii=False)
            
            json_path = os.path.join(out_dir, "owui_index.json")
            self._atomic_write(json_path, json_content)
            
            # --- Render Markdown ---
            md_path = os.path.join(out_dir, "OWUI_INDEX.md")
            md_lines = [
                "# 🧩 Open WebUI Extension Index",
                f"\n*Auto-generated at {index_data['generated_at']}*",
                "\n---",
                "\n## 📊 Summary",
                "\n| Category | Count |",
                "| :--- | ---: |",
                f"| Models | {len(index_data.get('models', []))} |",
                f"| Tools (Installed) | {len(index_data.get('tools_installed', []))} |",
                f"| Functions (Installed) | {len(index_data.get('functions_installed', []))} |",
                f"| Community Tools | {len(index_data.get('tools_available', []))} |",
                f"| Community Functions | {len(index_data.get('functions_available', []))} |",
            ]

            md_lines.append("\n---\n\n## 🔧 Tools — Community Catalog")
            md_lines.append("| Name | Description | Install |")
            md_lines.append("| :--- | :--- | :--- |")
            for t in index_data.get("tools_available", [])[:50]:
                md_lines.append(f"| {t['name']} | {t['description'][:100]} | [Link]({t['install_url']}) |")

            self._atomic_write(md_path, "\n".join(md_lines))

            report.append(f"\n✅ **Index Saved**: `{json_path}` and `{md_path}`")
            report.append(f"**Finished**: {datetime.now(timezone.utc).isoformat()}")
            
            return "\n".join(report)
        except Exception as e:
            return f"❌ Failed to save index: {str(e)}"
