import json
import os
import pytest
from owui_index_generator.tools.extension_search import Tools

@pytest.fixture
def search_tool(tmp_path):
    tool = Tools()
    index_file = tmp_path / "index.json"
    index_data = {
        "generated_at": "2024-01-01",
        "models": [{"id": "m1", "name": "Model 1", "description": "AI Model"}],
        "prompts": [{"command": "/test", "title": "Test Prompt"}],
        "tools_installed": [{"id": "t_inst", "name": "Installed Tool", "meta": {"description": "Local search"}}],
        "tools_available": [{"slug": "t_comm", "name": "Community Tool", "description": "Web search", "author": "dev", "downloads": 100}]
    }
    index_file.write_text(json.dumps(index_data))
    tool.valves.index_path = str(index_file)
    return tool

def test_search_installed_priority(search_tool):
    # Query matching both 'Installed' and 'Community' via 'search'
    # Installed should be higher priority (SRCH-04)
    result = search_tool.search_extensions("search")
    
    # Check that Installed Tool appears first
    assert "### 1. Installed Tool" in result
    assert "### 2. Community Tool" in result

def test_search_models_prompts(search_tool):
    # Test model search
    res_model = search_tool.search_extensions("Model")
    assert "### 1. Model 1" in res_model
    assert "🤖 Model" in res_model
    
    # Test prompt search
    res_prompt = search_tool.search_extensions("Test")
    assert "### 1. Test Prompt" in res_prompt
    assert "📝 Prompt Template" in res_prompt

def test_error_visibility(tmp_path):
    tool = Tools()
    tool.valves.index_path = str(tmp_path / "missing.json")
    result = tool.search_extensions("query")
    assert "⚠️ Extension index not found" in result
    assert "Technical Error: File not found" in result

def test_author_normalization(search_tool):
    tool = search_tool
    assert tool._normalize_author("@username") == "username"
    assert tool._normalize_author("username") == "username"
    assert tool._normalize_author(None) == ""

def test_ellipsis_logic(search_tool):
    tool = search_tool
    # Short desc -> no ellipsis forced ideally, but the code does it if > 120
    # Let's check long desc
    long_desc = "X" * 150
    item = {"name": "Test", "id": "id", "description": long_desc, "status": "ok", "action": "X", "score": 1, "type": "T", "priority": 1}
    # We can't easily test private methods but we know what search returns
    
    # Inject long desc into index
    with open(tool.valves.index_path, "r") as f:
        data = json.load(f)
    data["models"][0]["description"] = long_desc
    with open(tool.valves.index_path, "w") as f:
        json.dump(data, f)
        
    result = tool.search_extensions("Model")
    assert "..." in result
    assert "XXXX" in result
