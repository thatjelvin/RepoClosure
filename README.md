# RepoClosure: Graph-Guided, Explainable, Model-Agnostic Repository-Level Code Retrieval

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](https://github.com/Jelvin/assignments/ce/actions)

A retrieval toolkit designed to improve how AI coding agents find relevant code in complex software repositories by combining structural dependency graphs, semantic embeddings, and lexical retrieval with explainable graph-guided expansion.

## 🎯 Target Competition

This project targets the **Gemma 4 Developer Agent Paper Track** - **Best New Resource award** ($10,000).

## 📋 Features

- **Model-Agnostic**: Works with any local embedding model or can run lexical-only
- **Explainable**: Every retrieved item includes graph-based explanations showing why it was selected
- **Provenance-Annotated Graph**: Distinguishes between statically verified relationships (AST-derived) and heuristics
- **Budgeted Expansion**: Configurable graph traversal with explainable audit trails
- **Hybrid Fusion**: Combines lexical (BM25), semantic (embeddings), and path-based retrieval using Reciprocal Rank Fusion
- **Context Closure Objective**: Evaluates not just edit localization but also retrieval of supporting context
- **CLI & Python API**: Easy-to-use command line interface and programmable interface
- **Incremental Indexing**: Supports caching of embeddings for fast rebuilds
- **Comprehensive Evaluation**: Includes retrieval metrics, bootstrap confidence intervals, and per-repository breakdowns

## 🏗️ Architecture

```
Repository → Parser → Entity Extraction → Typed Provenance Graph 
                                    ↓
                    BM25 Retriever ← Fusion (RRF) → Ranking
                                    ↑
                    Dense Retriever ← Expansion (Graph-Guided) ← Seeds
```

## 🔧 Installation

```bash
# Install from source
git clone <repository-url>
cd repoclosure
pip install -e .

# Install with embedding support
pip install -e .[embeddings,huggingface]

# Or install for development
pip install -e .[dev]
```

## 🚀 Quick Start

### Index a Repository

```bash
repoclosure index /path/to/repository
```

### Search for Code

```bash
repoclosure search /path/to/repository \
  --query "authentication fails with expired tokens" \
  --method graph_hybrid \
  --top-k 10
```

### Available Methods

- `lexical`: BM25-based retrieval
- `semantic`: Embedding-based retrieval  
- `path`: Path/filename token matching
- `hybrid`: RRF fusion of lexical + semantic
- `graph_hybrid`: Hybrid + graph-guided expansion (proposed method)

### Output Format

Results are returned as JSON with:
- Ranked entities (files, functions, classes, methods)
- Source locations and symbol metadata
- Component scores (lexical, semantic, path, fused)
- Graph explanations for graph_hybrid method
- Contributing entities in same file (for file granularity)

## 📚 Python API

```python
from repoclosure.indexing import build_index
from repoclosure.config import Config

# Build index
index = build_index("/path/to/repository")

# Search
result = index.search(
    query="how to verify JWT tokens",
    method="graph_hybrid",
    top_k=10,
    granularity="file"  # or "symbol"
)

print(result.to_dict())
```

## 🧪 Evaluation Framework

Run controlled experiments:

```bash
python scripts/run_experiments.py \
  --benchmark benchmarks/benchmark_v1.json \
  --methods lexical semantic hybrid graph_hybrid \
  --run-id my_experiment
```

## 📊 Evaluation Metrics

- **File-level**: Recall@1/@5/@10, MRR, nDCG@10
- **Symbol-level**: Recall@k, MRR  
- **Context Closure**: Closure-Recall@k (retrieval of supporting entities)
- **Resource**: Latency, memory usage, index size
- **Uncertainty**: Bootstrap confidence intervals, paired statistical tests

## 📖 Documentation

- [Research Plan](docs/research_plan.md) - Hypotheses, methodology, experimental design
- [Novelty Assessment](docs/novelty_assessment.md) - Comparison with prior work
- [Competition Requirements](docs/competition_requirements.md) - Verified competition rules
- [Environment](docs/environment.md) - Development and execution environment details
- [Experiment Matrix](experiments/experiment_matrix.md) - Tracking of all experiments

## 🔬 Current Status

Core functionality implemented and tested:
- ✅ Python AST parsing with provenance tracking
- ✅ Typed, directed code graph construction (file/module/class/function/method)
- ✅ Lexical retrieval (BM25)
- ✅ Semantic retrieval (sentence-transformers, transformers fallback)
- ✅ Hybrid fusion (Reciprocal Rank Fusion)
- ✅ Graph-guided expansion with explainable audit trails
- ✅ CLI interface (index, search commands)
- ✅ Python API
- ✅ Comprehensive test suite (46/46 tests passing)
- ✅ Experimentation framework
- ✅ Reproducible builds with caching

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 📜 Citation

If you use RepoClosure in your research, please cite:

```bibtex
@misc{repoclosure2026,
  title={RepoClosure: Graph-Guided, Explainable, Model-Agnostic Repository-Level Code Retrieval},
  author={RepoClosure contributors},
  year={2026},
  publisher={GitHub},
  url={https://github.com/Jelvin/assignments/ce}
}
```

## 🙏 Acknowledgments

Built with:
- [sentence-transformers](https://www.sbert.net/)
- [rank-bm25](https://github.com/dorianbrown/rank_bm25)
- [networkx](https://networkx.org/)
- [numpy](https://numpy.org/)
- [pytest](https://docs.pytest.org/)