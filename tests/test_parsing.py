from repoclosure.config import Config
from repoclosure.indexing import RepositoryIndex
from repoclosure.parsing import parse_repository, walk_repository


def test_walk_respects_ignores(synthetic_repo):
    files = walk_repository(synthetic_repo)
    assert "pkg/core.py" in files
    assert all("__pycache__" not in f for f in files)
    assert all(not f.endswith(".md") for f in files)


def test_entities_and_kinds(synthetic_repo):
    parsed = parse_repository(synthetic_repo)
    kinds = {}
    for e in parsed.entities.values():
        kinds[e.kind] = kinds.get(e.kind, 0) + 1
    assert kinds.get("file", 0) >= 4
    assert kinds.get("module", 0) >= 4
    assert kinds.get("function", 0) >= 3
    assert kinds.get("class", 0) >= 1
    assert kinds.get("method", 0) >= 1


def test_async_flag_and_source_locations(synthetic_repo):
    parsed = parse_repository(synthetic_repo)
    fetch = next(e for e in parsed.entities.values() if e.name == "fetch")
    assert fetch.is_async is True
    assert fetch.start_line >= 1 and fetch.end_line >= fetch.start_line
    run = next(e for e in parsed.entities.values() if e.name == "run")
    assert not run.is_async


def test_malformed_file_recorded_not_dropped(synthetic_repo):
    parsed = parse_repository(synthetic_repo)
    errors = {e.file: e for e in parsed.errors}
    assert "pkg/broken.py" in errors
    assert errors["pkg/broken.py"].error_type == "SyntaxError"
    # the file is still represented so it is not silently discarded
    assert any(e.file == "pkg/broken.py" for e in parsed.entities.values())


def test_deterministic_indexing(synthetic_repo, hashing_config):
    a = RepositoryIndex(synthetic_repo, hashing_config).build()
    b = RepositoryIndex(synthetic_repo, hashing_config).build()
    assert set(a.entities) == set(b.entities)
    ra = a.search("helper util", method="lexical")
    rb = b.search("helper util", method="lexical")
    assert [i.id for i in ra.items] == [i.id for i in rb.items]
