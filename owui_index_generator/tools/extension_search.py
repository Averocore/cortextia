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
        self._last_error = "" # SRCH-01: Track last error

    def _load_index(self) -> dict:
        """Load index with simple file-mtime caching."""
        path = self.valves.index_path
        if not os.path.exists(path):
            self._last_error = f"File not found: {path}"
            return {}

        try:
            mtime = os.path.getmtime(path)
            if self._index_cache is None or mtime > self._cache_mtime:
                with open(path, "r", encoding="utf-8") as f:
                    self._index_cache = json.load(f)
                self._cache_mtime = mtime
            return self._index_cache
        except Exception as e:
            self._last_error = f"Load error: {str(e)}"
            return {}

    def _score_match(self, query_terms: list[str], text: str) -> int:
        """Simple relevance scoring: count how many query terms appear."""
        text_lower = text.lower()
        return sum(1 for term in query_terms if term in text_lower)

    def _normalize_author(self, author: Optional[str]) -> str:
        """SRCH-02: Normalize author formatting."""
        if not author:
            return ""
        return author.lstrip("@")

    def search_extensions(
        self,
        query: str,
        category: Optional[str] = None,
    ) -> str:
        """
        Search for Open WebUI extensions (tools, functions, models, prompts)
        that match a described need or keyword.
        """
        index = self._load_index()
        if not index:
            error_msg = f"⚠️ Extension index not found at path: {self.valves.index_path}"
            if self._last_error:
                 error_msg += f"\n(Technical Error: {self._last_error})"
            return error_msg + "\n\nEnsure the index generator has run and the file is accessible."

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
                        "priority": 2, # SRCH-04: Higher priority for installed
                        "type": "🔧 Installed Tool",
                        "name": tool.get("name", "Unknown"),
                        "id": tool.get("id", ""),
                        "description": (meta.get("description") or ""),
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
                        "priority": 2,
                        "type": f"⚙️ Installed Function ({ftype})",
                        "name": func.get("name", "Unknown"),
                        "id": func.get("id", ""),
                        "description": (meta.get("description") or ""),
                        "status": "✅ Installed",
                        "action": "Already available — check Workspace > Functions",
                    })

        # --- Search models (SRCH-05) ---
        if category in (None, "models"):
            for model in index.get("models", []):
                searchable = f"{model.get('name', '')} {model.get('id', '')} {model.get('description', '')}"
                score = self._score_match(query_terms, searchable)
                if score > 0:
                    results.append({
                        "score": score,
                        "priority": 1,
                        "type": "🤖 Model",
                        "name": model.get("name", "Unknown"),
                        "id": model.get("id", ""),
                        "description": (model.get("description") or ""),
                        "status": "✅ Configured",
                        "action": "Available as a model in chat",
                    })

        # --- Search prompts (SRCH-05) ---
        if category in (None, "prompts"):
            for prompt in index.get("prompts", []):
                searchable = f"{prompt.get('title', '')} {prompt.get('command', '')}"
                score = self._score_match(query_terms, searchable)
                if score > 0:
                    results.append({
                        "score": score,
                        "priority": 1,
                        "type": "📝 Prompt Template",
                        "name": prompt.get("title") or prompt.get("command", "Unknown"),
                        "id": prompt.get("command", ""),
                        "description": "Custom prompt template",
                        "status": "✅ Available",
                        "action": f"Use in chat via {prompt.get('command')}",
                    })

        # --- Search community tools ---
        if category in (None, "community_tools", "tools_available"):
            for ext in index.get("tools_available", []):
                searchable = f"{ext.get('name', '')} {ext.get('description', '')}"
                score = self._score_match(query_terms, searchable)
                if score > 0:
                    results.append({
                        "score": score,
                        "priority": 0,
                        "type": "🌐 Community Tool",
                        "name": ext.get("name", "Unknown"),
                        "id": ext.get("slug", ""),
                        "description": ext.get("description") or "",
                        "status": "📥 Available",
                        "action": f"Install → {ext.get('install_url', 'openwebui.com')}",
                        "downloads": ext.get("downloads", 0),
                        "author": self._normalize_author(ext.get("author")),
                    })

        # --- Search community functions ---
        if category in (None, "community_functions", "functions_available"):
            for ext in index.get("functions_available", []):
                searchable = f"{ext.get('name', '')} {ext.get('description', '')}"
                score = self._score_match(query_terms, searchable)
                if score > 0:
                    results.append({
                        "score": score,
                        "priority": 0,
                        "type": "🌐 Community Function",
                        "name": ext.get("name", "Unknown"),
                        "id": ext.get("slug", ""),
                        "description": ext.get("description") or "",
                        "status": "📥 Available",
                        "action": f"Install → {ext.get('install_url', 'openwebui.com')}",
                        "downloads": ext.get("downloads", 0),
                        "author": self._normalize_author(ext.get("author")),
                    })

        if not results:
            return (
                f"No extensions found matching '{query}'.\n\n"
                f"💡 Suggestions:\n"
                f"- Try broader terms (e.g., 'search' instead of 'SearXNG')\n"
                f"- Browse the community: https://openwebui.com/tools\n"
            )

        # SRCH-04: Sort by score (desc), then priority (desc), then downloads (desc)
        results.sort(
            key=lambda r: (r["score"], r["priority"], r.get("downloads", 0)),
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
            
            # SRCH-03: Fixed ellipsis behavior
            desc = r['description']
            if len(desc) > 120:
                desc = desc[:120].strip() + "..."
            lines.append(f"- **Description:** {desc}")
            
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

    def get_index_summary(self) -> str:
        """
        Get a high-level summary of the extension index — how many tools, 
        functions, models, and community extensions are cataloged.
        """
        index = self._load_index()
        if not index:
            error_msg = "⚠️ Extension index not found."
            if self._last_error:
                error_msg += f" (Error: {self._last_error})"
            return error_msg

        tools = len(index.get("tools_installed", []))
        functions = len(index.get("functions_installed", []))
        models = len(index.get("models", []))
        prompts = len(index.get("prompts", []))
        knowledge = len(index.get("knowledge_bases", []))
        
        comm_tools = len(index.get("tools_available", []))
        comm_funcs = len(index.get("functions_available", []))

        generated = index.get("generated_at", "unknown")

        return (
            f"## 📊 Extension Index Summary\n\n"
            f"**Last generated:** {generated}\n\n"
            f"| Category | Count |\n"
            f"|----------|-------|\n"
            f"| Installed Tools | {tools} |\n"
            f"| Installed Functions | {functions} |\n"
            f"| Available Models | {models} |\n"
            f"| Prompts | {prompts} |\n"
            f"| Knowledge Bases | {knowledge} |\n"
            f"| Community Tools (catalog) | {comm_tools} |\n"
            f"| Community Functions (catalog) | {comm_funcs} |\n"
            f"| **Total Cataloged** | **{tools + functions + models + prompts + knowledge + comm_tools + comm_funcs}** |\n"
        )
