"""
Pydantic schemas for Open WebUI extensions.
Designed from real API response samples (Step 1D output).
"""

from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Models  (/api/models  →  {"data": [...]} )
# ---------------------------------------------------------------------------

class ModelArchitecture(BaseModel):
    modality: Optional[str] = None
    input_modalities: list[str] = []
    output_modalities: list[str] = []
    tokenizer: Optional[str] = None
    instruct_type: Optional[str] = None

class ModelPricing(BaseModel):
    prompt: Optional[str] = None
    completion: Optional[str] = None
    image: Optional[str] = None
    audio: Optional[str] = None
    web_search: Optional[str] = None
    internal_reasoning: Optional[str] = None
    input_cache_read: Optional[str] = None
    input_cache_write: Optional[str] = None

class ModelTopProvider(BaseModel):
    context_length: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    is_moderated: Optional[bool] = None

class ModelEntry(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    context_length: Optional[int] = None
    architecture: Optional[ModelArchitecture] = None
    pricing: Optional[ModelPricing] = None
    top_provider: Optional[ModelTopProvider] = None
    supported_parameters: list[str] = []
    connection_type: Optional[str] = None   # "external" = OpenRouter via API
    owned_by: Optional[str] = None
    tags: list[Any] = []
    actions: list[Any] = []
    filters: list[Any] = []
    # Derived for the index
    source: str = "openrouter"              # "ollama" | "openrouter" | "custom"

class ModelsResponse(BaseModel):
    data: list[ModelEntry] = []


# ---------------------------------------------------------------------------
# Tools  (/api/v1/tools/  →  [...] )
# Match Open WebUI's tool object shape (empty now; schema based on API docs)
# ---------------------------------------------------------------------------

class ToolMeta(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    manifest: Optional[dict[str, Any]] = None   # tags, requirements, etc.

class ToolValve(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    default: Optional[Any] = None

class ToolEntry(BaseModel):
    id: str
    user_id: Optional[str] = None
    name: str
    content: Optional[str] = None           # Python source code
    meta: Optional[ToolMeta] = None
    is_active: bool = True
    updated_at: Optional[int] = None
    created_at: Optional[int] = None
    # Derived for index
    install_url: Optional[str] = None       # https://openwebui.com/t/{author}/{slug}
    status: str = "installed"               # "installed" | "available" | "update_available"


# ---------------------------------------------------------------------------
# Functions  (/api/v1/functions/  →  [...] )
# ---------------------------------------------------------------------------

class FunctionMeta(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    manifest: Optional[dict[str, Any]] = None

class FunctionEntry(BaseModel):
    id: str
    user_id: Optional[str] = None
    name: str
    type: str = "pipe"                      # "pipe" | "filter" | "action"
    content: Optional[str] = None
    meta: Optional[FunctionMeta] = None
    is_active: bool = True
    is_global: bool = False
    updated_at: Optional[int] = None
    created_at: Optional[int] = None
    # Derived for index
    install_url: Optional[str] = None
    status: str = "installed"


# ---------------------------------------------------------------------------
# Prompts  (/api/v1/prompts/  →  [...] )
# ---------------------------------------------------------------------------

class PromptEntry(BaseModel):
    command: str                            # e.g. "/summarize"
    user_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    timestamp: Optional[int] = None
    source: str = "local"                  # "local" | "community"


# ---------------------------------------------------------------------------
# Knowledge  (/api/v1/knowledge/  →  {"items": [...], "total": int} )
# ---------------------------------------------------------------------------

class KnowledgeEntry(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    user_id: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    meta: Optional[dict[str, Any]] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None

class KnowledgeResponse(BaseModel):
    items: list[KnowledgeEntry] = []
    total: int = 0


# ---------------------------------------------------------------------------
# Community extension (from openwebui.com scraping — Step 3)
# ---------------------------------------------------------------------------

class CommunityExtension(BaseModel):
    slug: str
    name: str
    type: str                               # "tool" | "function" | "model" | "prompt"
    subtype: Optional[str] = None           # "pipe" | "filter" | "action"
    description: Optional[str] = None
    author: Optional[str] = None
    downloads: Optional[int] = None
    tags: list[str] = []
    install_url: str                        # https://openwebui.com/t/{author}/{slug}
    source_url: Optional[str] = None        # GitHub raw .py URL
    requires_api_key: bool = False
    dependencies: list[str] = []           # API keys, external services needed
    status: str = "available"              # "available" | "installed" | "update_available"


# ---------------------------------------------------------------------------
# Unified index snapshot
# ---------------------------------------------------------------------------

class OWUIIndex(BaseModel):
    generated_at: str
    instance_url: str
    version: Optional[str] = None
    models: list[ModelEntry] = []
    tools_installed: list[ToolEntry] = []
    tools_available: list[CommunityExtension] = []
    functions_installed: list[FunctionEntry] = []
    functions_available: list[CommunityExtension] = []
    prompts: list[PromptEntry] = []
    knowledge_bases: list[KnowledgeEntry] = []
