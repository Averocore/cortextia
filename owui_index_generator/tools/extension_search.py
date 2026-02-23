"""
title: Extension Catalog Search
author: Cortextia
author_url: https://github.com/Averocore/cortextia
version: 1.0.0
description: Searches the OWUI extension index to find tools, functions, models, and prompts matching a user's needs. Returns structured recommendations with install links.
required_open_webui_version: 0.4.0
"""

import json
import os
from typing import Optional
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        index_path: str = Field(
            default="/app/backend/data/owui_index.json",
            description="Path to the owui_index.json file inside the container",
        )
        max_results: int = Field(
            default=10,
            description="Maximum number of results to return per search",
        )

    def __init__(self):
        self.valves = self.Valves()
        self._index_cache = None
        self._cache_mtime = 0

    def _load_index(self) -> dict:
        """Load index with simple file-mtime caching."""
        path = self.valves.index_path
        if not os.path.exists(path):
            return {}

        try:
            mtime = os.path.getmtime(path)
            if self._index_cache is None or mtime > self._cache_mtime:
                with open(path, "r", encoding="utf-8") as f:
                    self._index_cache = json.load(f)
                self._cache_mtime = mtime
            return self._index_cache
        except Exception:
            return {}

    def _score_match(self, query_terms: list[str], text: str) -> int:
        """Simple relevance scoring: count how many query terms appear."""
        text_lower = text.lower()
        return sum(1 for term in query_terms if term in text_lower)

    def search_extensions(
        self,
        query: str,
        category: Optional[str] = None,
    ) -> str:
        """
        Search for Open WebUI extensions (tools, functions, models, prompts)
        that match a described need or keyword.

        Use this when a user asks about capabilities, wants recommendations,
        or asks "is there a tool/function for X?"

        :param query: What the user needs, e.g. "web search", "image generation",
                      "code execution", "TTS", "RAG", etc.
        :param category: Optional filter — one of: "tools", "functions", "models",
                         "prompts", "community_tools", "community_functions".
                         Leave empty to search everything.
        :return: Formatted list of matching extensions with install info.
        """
        index = self._load_index()
        if not index:
            return (
                "⚠️ Extension index not found at path: " + self.valves.index_path + 
                "\n\nEnsure the index generator has run and the file is accessible."
            )

        query_terms = [t.strip().lower() for t in query.split() if len(t) > 2]
        if not query_terms:
            return "Please provide a more specific search query (at least 3 characters)."

        results = []

        # --- Search installed tools ---
        if category in (None, "tools"):
            for tool in index.get("tools_installed", []):
                meta = tool.get("meta", {})
                searchable = f"{tool.get('name', '')} {meta.get('description', '')}"
                score = self._score_match(query_terms, searchable)
                if score > 0:
                    results.append({
                        "score": score,
                        "type": "🔧 Installed Tool",
                        "name": tool.get("name", "Unknown"),
                        "id": tool.get("id", ""),
                        "description": (meta.get("description") or "")[:120],
                        "status": "✅ Installed",
                        "action": "Already available — assign to a model in Workspace > Models",
                    })

        # --- Search installed functions ---
        if category in (None, "functions"):
            for func in index.get("functions_installed", []):
                meta = func.get("meta", {})
                searchable = (
                    f"{func.get('name', '')} {meta.get('description', '')} "
                    f"{func.get('type', '')}"
                )
                score = self._score_match(query_terms, searchable)
                if score > 0:
                    ftype = func.get("type", "unknown").title()
                    results.append({
                        "score": score,
                        "type": f"⚙️ Installed Function ({ftype})",
                        "name": func.get("name", "Unknown"),
                        "id": func.get("id", ""),
                        "description": (meta.get("description") or "")[:120],
                        "status": "✅ Installed",
                        "action": "Already available — check Workspace > Functions",
                    })

        # --- Search community tools ---
        if category in (None, "community_tools", "tools_available"):
            for ext in index.get("tools_available", []):
                searchable = f"{ext.get('name', '')} {ext.get('description', '')}"
                score = self._score_match(query_terms, searchable)
                if score > 0:
                    results.append({
                        "score": score,
                        "type": "🌐 Community Tool",
                        "name": ext.get("name", "Unknown"),
                        "id": ext.get("slug", ""),
                        "description": (ext.get("description") or "")[:120],
                        "status": "📥 Available",
                        "action": f"Install → {ext.get('install_url', 'openwebui.com')}",
                        "downloads": ext.get("downloads", 0),
                        "author": ext.get("author", ""),
                    })

        # --- Search community functions ---
        if category in (None, "community_functions", "functions_available"):
            for ext in index.get("functions_available", []):
                searchable = f"{ext.get('name', '')} {ext.get('description', '')}"
                score = self._score_match(query_terms, searchable)
                if score > 0:
                    results.append({
                        "score": score,
                        "type": "🌐 Community Function",
                        "name": ext.get("name", "Unknown"),
                        "id": ext.get("slug", ""),
                        "description": (ext.get("description") or "")[:120],
                        "status": "📥 Available",
                        "action": f"Install → {ext.get('install_url', 'openwebui.com')}",
                        "downloads": ext.get("downloads", 0),
                        "author": ext.get("author", ""),
                    })

        if not results:
            return (
                f"No extensions found matching '{query}'.\n\n"
                f"💡 Suggestions:\n"
                f"- Try broader terms (e.g., 'search' instead of 'SearXNG')\n"
                f"- Browse the community: https://openwebui.com/tools\n"
            )

        # Sort by relevance score, then by downloads for community items
        results.sort(
            key=lambda r: (r["score"], r.get("downloads", 0)),
            reverse=True,
        )
        results = results[: self.valves.max_results]

        # Format output
        lines = [f"## 🔍 Search Results for: \"{query}\"\n"]
        lines.append(f"Found **{len(results)}** matching extensions:\n")

        for i, r in enumerate(results, 1):
            lines.append(f"### {i}. {r['name']}")
            lines.append(f"- **Type:** {r['type']}")
            lines.append(f"- **ID:** `{r['id']}`")
            lines.append(f"- **Description:** {r['description']}...")
            lines.append(f"- **Status:** {r['status']}")
            if r.get("author"):
                lines.append(f"- **Author:** @{r['author']}")
            if r.get("downloads"):
                lines.append(f"- **Downloads:** {r['downloads']:,}")
            lines.append(f"- **Action:** {r['action']}")
            lines.append("")

        lines.append("---")
        lines.append(
            "⚠️ **Security:** Only install extensions from trusted sources. "
            "Review code before importing."
        )

        return "\n".join(lines)
