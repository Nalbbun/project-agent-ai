from app.services.llm_client import AgentLLMClient


client = AgentLLMClient()


def test_parse_plain_json():
    payload = client._parse_json_like('{"summary": "ok"}')
    assert payload["summary"] == "ok"


def test_parse_code_fence_json():
    payload = client._parse_json_like('```json\n{"summary": "ok"}\n```')
    assert payload["summary"] == "ok"


def test_parse_json_embedded_in_text():
    payload = client._parse_json_like('result below\n{"summary": "ok", "items": []}\nend')
    assert payload["summary"] == "ok"
