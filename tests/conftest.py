import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from repoclosure.config import Config  # noqa: E402
from repoclosure.indexing import RepositoryIndex  # noqa: E402

SAMPLE_REPO = ROOT / "examples" / "sample_repo"


@pytest.fixture
def hashing_config() -> Config:
    cfg = Config()
    cfg.retrieval.embed_model = "hashing"
    return cfg


@pytest.fixture
def synthetic_repo(tmp_path: Path) -> Path:
    """A deterministic repository with a known call/import structure."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("from .core import run\n", encoding="utf-8")
    (tmp_path / "pkg" / "core.py").write_text(
        "from .util import helper\n\n"
        "async def fetch():\n    return 1\n\n"
        "def run():\n    return helper()\n\n"
        "class Engine:\n"
        "    def start(self):\n        return run()\n",
        encoding="utf-8",
    )
    (tmp_path / "pkg" / "util.py").write_text(
        "def helper():\n    return 42\n\n"
        "def unused():\n    return 0\n",
        encoding="utf-8",
    )
    (tmp_path / "pkg" / "broken.py").write_text("def bad(:\n    pass\n", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "junk.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# demo\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def sample_index(hashing_config: Config) -> RepositoryIndex:
    return RepositoryIndex(SAMPLE_REPO, hashing_config).build()
