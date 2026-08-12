import pytest
from qbc_workbench.llm import OllamaClient

def test_schema_validation_rejects_missing_keys(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"message":{"content":"{\"unexpected\":1}"}}
    monkeypatch.setattr("requests.post",lambda *a,**k:Response())
    schema={"type":"object","properties":{"value":{"type":"string"}},"required":["value"]}
    with pytest.raises(ValueError,match="missing: value"):
        OllamaClient().extract("task","text",schema)
