"""RepoClosure — model-agnostic, explainable, graph-guided repository code retrieval.

Public API
----------
build_index(root, config)      -> RepositoryIndex
RepositoryIndex.search(...)    -> RetrievalResult
"""

from .config import Config, load_config
from .indexing import RepositoryIndex, build_index
from .graph import CodeGraph
from .parsing import Entity, parse_repository, walk_repository

__all__ = [
    "Config",
    "load_config",
    "RepositoryIndex",
    "build_index",
    "CodeGraph",
    "Entity",
    "parse_repository",
    "walk_repository",
]

__version__ = "0.1.0"
