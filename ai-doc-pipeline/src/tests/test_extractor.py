from pathlib import Path
from ai_doc_pipeline.extractor import extract_entities

def test_extract_basic_function(tmp_path: Path):
    (tmp_path / "test.py").write_text(
        "def hello(name: str) -> str:\n    '''Приветствие.'''\n    return f'Привет {name}'\n",
        encoding="utf-8",
    )
    entities = list(extract_entities(tmp_path))
    assert len(entities) == 1
    ent, snippet = entities[0]
    assert ent.name == "hello"
    assert ent.kind == "function"
    assert "def hello" in ent.signature
    assert "Приветствие" in ent.original_doc
    assert "f'Привет {name}'" in snippet