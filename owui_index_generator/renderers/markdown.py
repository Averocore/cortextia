"""
renderers/markdown.py — Step 5
Renders an OWUIIndex object into OWUI_INDEX.md using Jinja2.
"""

from __future__ import annotations
import os
import logging
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from owui_index_generator.schema.extension import OWUIIndex

log = logging.getLogger(__name__)

# Templates live at owui_index_generator/templates/
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _unix_to_date(ts: int | None) -> str:
    """Custom Jinja2 filter: convert Unix timestamp to readable date string."""
    if not ts:
        return "—"
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return str(ts)


def _build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape([]),   # No HTML escaping — we're writing Markdown
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["unix_to_date"] = _unix_to_date
    return env


def render_index(index: OWUIIndex) -> str:
    """Render the OWUIIndex into a Markdown string using the Jinja2 template."""
    env = _build_env()
    template = env.get_template("index.md.j2")
    content = template.render(index=index)
    log.info("Markdown rendered successfully.")
    return content


def save_index(content: str, path: str | Path = "data/OWUI_INDEX.md") -> Path:
    """Write the rendered Markdown string to disk, creating directories as needed."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    log.info(f"OWUI_INDEX.md saved to {out.resolve()}")
    return out
