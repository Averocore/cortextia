"""
local_api.py — Step 2
Collects all installed extensions from a local Open WebUI instance.
Uses the real API response shapes validated in Step 1D.
"""

from __future__ import annotations
import os
import json
import logging
from datetime import datetime, timezone
from typing import Any

import requests
from dotenv import load_dotenv

# Add the parent dir to path so we can import the schema
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from owui_index_generator.schema.extension import (
    ModelsResponse, ModelEntry,
    ToolEntry, ToolMeta,
    FunctionEntry, FunctionMeta,
    PromptEntry,
    KnowledgeResponse, KnowledgeEntry,
    OWUIIndex,
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


class LocalAPICollector:
    """Fetches all installed content from a running Open WebUI instance."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.getenv("WEBUI_URL", "http://localhost:7860")).rstrip("/")
        self.api_key  = api_key or os.getenv("WEBUI_API_KEY", "")
        self.session  = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        })

    # ------------------------------------------------------------------
    # Low-level fetch helper
    # ------------------------------------------------------------------
    def _get(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            log.warning(f"HTTP {e.response.status_code} for {url}: {e.response.text[:200]}")
            return None
        except Exception as e:
            log.warning(f"Error fetching {url}: {e}")
            return None

    # ------------------------------------------------------------------
    # Resource collectors
    # ------------------------------------------------------------------
    def get_version(self) -> str | None:
        data = self._get("/api/config")
        if data:
            return data.get("version")
        return None

    def get_models(self) -> list[ModelEntry]:
        raw = self._get("/api/models")
        if not raw:
            return []
        try:
            resp = ModelsResponse.model_validate(raw)
            log.info(f"  Models: {len(resp.data)} found")
            return resp.data
        except Exception as e:
            log.warning(f"Failed to parse models: {e}")
            return []

    def get_tools(self) -> list[ToolEntry]:
        raw = self._get("/api/v1/tools/") or []
        tools = []
        for item in raw:
            try:
                tool = ToolEntry.model_validate(item)
                tools.append(tool)
            except Exception as e:
                log.warning(f"Skipping tool {item.get('id', '?')}: {e}")
        log.info(f"  Tools: {len(tools)} installed")
        return tools

    def get_functions(self) -> list[FunctionEntry]:
        raw = self._get("/api/v1/functions/") or []
        functions = []
        for item in raw:
            try:
                fn = FunctionEntry.model_validate(item)
                functions.append(fn)
            except Exception as e:
                log.warning(f"Skipping function {item.get('id', '?')}: {e}")
        log.info(f"  Functions: {len(functions)} installed")
        return functions

    def get_prompts(self) -> list[PromptEntry]:
        raw = self._get("/api/v1/prompts/") or []
        prompts = []
        for item in raw:
            try:
                prompt = PromptEntry.model_validate(item)
                prompts.append(prompt)
            except Exception as e:
                log.warning(f"Skipping prompt {item.get('command', '?')}: {e}")
        log.info(f"  Prompts: {len(prompts)} found")
        return prompts

    def get_knowledge(self) -> list[KnowledgeEntry]:
        raw = self._get("/api/v1/knowledge/")
        if not raw:
            return []
        try:
            resp = KnowledgeResponse.model_validate(raw)
            log.info(f"  Knowledge bases: {resp.total} found")
            return resp.items
        except Exception as e:
            log.warning(f"Failed to parse knowledge: {e}")
            return []

    # ------------------------------------------------------------------
    # Main collect entry point
    # ------------------------------------------------------------------
    def collect(self) -> OWUIIndex:
        log.info(f"Collecting from {self.base_url} ...")
        version = self.get_version()
        models    = self.get_models()
        tools     = self.get_tools()
        functions = self.get_functions()
        prompts   = self.get_prompts()
        knowledge = self.get_knowledge()

        index = OWUIIndex(
            generated_at=datetime.now(timezone.utc).isoformat(),
            instance_url=self.base_url,
            version=version,
            models=models,
            tools_installed=tools,
            functions_installed=functions,
            prompts=prompts,
            knowledge_bases=knowledge,
        )
        log.info("Collection complete.")
        return index


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------
if __name__ == "__main__":
    collector = LocalAPICollector()
    index = collector.collect()

    out_path = "owui_index.json"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(index.model_dump_json(indent=2))

    log.info(f"Index saved to {out_path}")
    print(f"\n✅ Done! Models: {len(index.models)}, Tools: {len(index.tools_installed)}, "
          f"Functions: {len(index.functions_installed)}, Prompts: {len(index.prompts)}, "
          f"Knowledge: {len(index.knowledge_bases)}")
