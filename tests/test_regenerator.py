import json
import requests
import pytest
import responses
from owui_index_generator.tools.index_regenerator import Tools

@pytest.fixture
def regenerator():
    reg = Tools()
    reg.valves.output_dir = "test_output"
    reg.valves.api_key = "test_key"
    return reg

def test_api_key_env_fallback(monkeypatch):
    reg = Tools()
    reg.valves.api_key = ""
    monkeypatch.setenv("WEBUI_API_KEY", "env_key")
    assert reg._get_api_key() == "env_key"

def test_atomic_write(regenerator, tmp_path):
    out_file = tmp_path / "test.json"
    regenerator._atomic_write(str(out_file), '{"test": "data"}')
    assert out_file.exists()
    assert out_file.read_text() == '{"test": "data"}'

@responses.activate
def test_fetch_community_retry(regenerator):
    api_url = "https://api.openwebui.com/api/v1/posts/search?page=1&type=tool"
    
    # First attempt fails, second succeeds
    responses.add(responses.GET, api_url, status=500)
    responses.add(responses.GET, api_url, json={"items": [{"id": "t1", "title": "Tool 1"}]}, status=200)
    
    session = requests.Session() # Use standard requests Session, responses will intercept
    items = regenerator._fetch_community(session, "tools", 1)
    
    assert len(items) == 1
    assert items[0]["id"] == "t1"

@responses.activate
def test_regenerate_index_integration(regenerator, tmp_path):
    import requests # Ensure it's available in scope
    regenerator.valves.output_dir = str(tmp_path)
    base = regenerator.valves.owui_base_url
    
    # Mock local endpoints
    for endpoint in ["/api/models", "/api/v1/tools", "/api/v1/functions", "/api/prompts", "/api/v1/knowledge"]:
        responses.add(responses.GET, f"{base}{endpoint}", json=[], status=200)
        
    # Mock community
    responses.add(responses.GET, "https://api.openwebui.com/api/v1/posts/search?page=1&type=tool", 
                  json={"items": [{"id": "c1", "title": "Comm Tool", "content": "Desc", "user": {"username": "u1"}}]}, status=200)
    responses.add(responses.GET, "https://api.openwebui.com/api/v1/posts/search?page=1&type=function", 
                  json={"items": []}, status=200)
    
    result = regenerator.regenerate_index()
    
    assert "Index Saved" in result
    assert (tmp_path / "owui_index.json").exists()
    assert (tmp_path / "OWUI_INDEX.md").exists()
    
    data = json.loads((tmp_path / "owui_index.json").read_text())
    assert len(data["tools_available"]) == 1
    assert data["tools_available"][0]["slug"] == "c1"
