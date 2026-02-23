#!/usr/bin/env python3
"""
generate_index.py — Step 6
Orchestrator: collects data from local Open WebUI, renders OWUI_INDEX.md and owui_index.json.

Usage:
  python generate_index.py                        # Full run, saves to ./data/
  python generate_index.py --output-dir ./output/ # Custom output directory
  python generate_index.py --json-only            # Skip markdown, save JSON only
  python generate_index.py --md-only              # Skip JSON, save markdown only
  python generate_index.py --verbose              # Enable debug logging
"""

from __future__ import annotations
import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add the project root to path
sys.path.insert(0, str(Path(__file__).parent))

from owui_index_generator.local_api import LocalAPICollector
from owui_index_generator.renderers.markdown import render_index, save_index
from owui_index_generator.schema.extension import OWUIIndex


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)-8s %(name)s — %(message)s"
    )


def save_json(index: OWUIIndex, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(index.model_dump_json(indent=2), encoding="utf-8")
    logging.getLogger(__name__).info(f"owui_index.json saved to {path.resolve()}")
    return path


def print_summary(index: OWUIIndex, md_path: Path | None, json_path: Path | None) -> None:
    divider = "─" * 50
    print(f"\n{divider}")
    print("✅  OWUI_INDEX generated successfully")
    print(divider)
    if md_path:
        print(f"   📄  Markdown  → {md_path.resolve()}")
    if json_path:
        print(f"   📋  JSON      → {json_path.resolve()}")
    print(divider)
    print(f"   🤖  Models      : {len(index.models)}")

    tools_count = len(index.tools_installed)
    print(f"   🔧  Tools       : {tools_count}" +
          ("  (install some from openwebui.com/tools!)" if tools_count == 0 else ""))

    fn_count = len(index.functions_installed)
    print(f"   ⚙️   Functions   : {fn_count}" +
          ("  (install some from openwebui.com/functions!)" if fn_count == 0 else ""))

    print(f"   📝  Prompts     : {len(index.prompts)}")
    print(f"   📚  Knowledge   : {len(index.knowledge_bases)}")
    print(f"   ⏱️   Generated   : {index.generated_at}")
    print(divider)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate OWUI_INDEX.md and owui_index.json from your Open WebUI instance."
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="./data",
        help="Directory to save output files (default: ./data)"
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Only save owui_index.json, skip Markdown"
    )
    parser.add_argument(
        "--md-only",
        action="store_true",
        help="Only save OWUI_INDEX.md, skip JSON"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose debug logging"
    )
    args = parser.parse_args()

    setup_logging(args.verbose)
    log = logging.getLogger(__name__)

    output_dir = Path(args.output_dir)
    md_path    = output_dir / "OWUI_INDEX.md"
    json_path  = output_dir / "owui_index.json"

    # 1. Collect
    try:
        index = LocalAPICollector().collect()
    except Exception as e:
        log.error(f"Failed to collect data: {e}")
        return 1

    # 2. Render & Save Markdown
    saved_md = None
    if not args.json_only:
        try:
            content = render_index(index)
            saved_md = save_index(content, md_path)
        except Exception as e:
            log.error(f"Failed to render/save Markdown: {e}")
            return 1

    # 3. Save JSON
    saved_json = None
    if not args.md_only:
        try:
            saved_json = save_json(index, json_path)
        except Exception as e:
            log.error(f"Failed to save JSON: {e}")
            return 1

    # 4. Print summary
    print_summary(index, saved_md, saved_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
