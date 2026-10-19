import json

from repoclosure.cli import main


def _config(tmp_path):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"retrieval": {"embed_model": "hashing", "top_k": 5}}), encoding="utf-8")
    return str(cfg)


def test_cli_index(synthetic_repo, tmp_path, capsys):
    code = main(["index", str(synthetic_repo), "--config", _config(tmp_path)])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["num_files"] >= 4
    assert "graph" in out


def test_cli_search_json(synthetic_repo, tmp_path, capsys):
    code = main(["search", str(synthetic_repo), "--config", _config(tmp_path),
                 "--query", "helper", "--method", "hybrid", "--top-k", "3"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["query"] == "helper"
    assert out["method"] == "hybrid"
    assert isinstance(out["results"], list)


def test_cli_writes_graph(synthetic_repo, tmp_path):
    g = tmp_path / "graph.json"
    code = main(["index", str(synthetic_repo), "--config", _config(tmp_path),
                 "--graph-out", str(g)])
    assert code == 0 and g.exists()
    payload = json.loads(g.read_text(encoding="utf-8"))
    assert payload["directed"] is True and payload["multigraph"] is True
    assert payload["nodes"] and "edges" in payload
