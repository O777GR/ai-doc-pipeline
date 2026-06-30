import pytest
from pathlib import Path
from ai_doc_pipeline.ai_client import AIClient
from ai_doc_pipeline.models import AIConfig

@pytest.mark.asyncio
async def test_cache_creation(tmp_path: Path, monkeypatch):
    cfg = AIConfig(cache_dir=tmp_path / "cache")
    client = AIClient(cfg)
    
    call_count = 0
    async def fake_post(*_, **__):
        nonlocal call_count; call_count += 1
        class Resp:
            def raise_for_status(self): pass
            def json(self): return {"choices": [{"message": {"content": "ok"}}]}
        return Resp()
    
    monkeypatch.setattr(client._client, "post", fake_post)
    
    r1 = await client.generate("sys", "user")
    r2 = await client.generate("sys", "user")
    
    assert r1 == r2 == "ok"
    assert call_count == 1
    assert any(p.suffix == ".json" for p in cfg.cache_dir.iterdir())
    await client.close()