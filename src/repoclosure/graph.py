"""Typed, provenance-annotated code graph and bounded graph traversal.

Node kinds
----------
``file``      physical source file (repository-relative path)
``module``    importable Python module (1:1 with a file in this version)
``class``     class definition
``function``  module-level function (including ``async def``)
``method``    function defined inside a class (including ``async def``)

Edge types and provenance
-------------------------
``contains``    file->module, module->class/function, class->method.  prov ``ast_contains``, conf 1.0
``imports``     module->module (resolved within the repository).       prov ``ast_import``,   conf 1.0/0.6
``calls``       callable->callable, resolved.                          prov ``ast_call``      conf 0.5-0.9
``calls``       callable->callable, unresolved name match.             prov ``name_heuristic`` conf 0.30
``references``  callable/module->class/function used as a name.        prov ``ast_reference`` conf 0.6

Confidence semantics (documented, not a probability in a Bayesian sense):
1.0 statically certain structural facts; 0.7-0.9 resolved via scope/import; 0.5 unique global
name; 0.30 non-unique name heuristic (only emitted when ``enable_heuristic_calls``).
"""
from __future__ import annotations

import json
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

import networkx as nx

from .config import GraphConfig
from .parsing import Entity, ParsedRepository


@dataclass
class ExpansionRecord:
    """An entity pulled into the context by graph traversal, with its reason."""

    node: str
    seed: str
    edge_type: str
    provenance: str
    confidence: float
    hop: int
    direction: str  # "out" | "in"


@dataclass
class CodeGraph:
    graph: nx.MultiDiGraph = field(default_factory=nx.MultiDiGraph)
    entities: dict[str, Entity] = field(default_factory=dict)
    resolution_stats: dict[str, int] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # convenience
    # ------------------------------------------------------------------ #
    def add_entity(self, entity: Entity) -> None:
        self.entities[entity.id] = entity
        self.graph.add_node(entity.id, kind=entity.kind, name=entity.name, file=entity.file)

    def add_edge(self, u: str, v: str, edge_type: str, provenance: str, confidence: float) -> None:
        if u == v or u not in self.graph or v not in self.graph:
            return
        # collapse duplicate identical (source, target, type, provenance) edges
        if self.graph.has_edge(u, v):
            for data in self.graph.get_edge_data(u, v).values():
                if data.get("type") == edge_type and data.get("provenance") == provenance:
                    return
        self.graph.add_edge(u, v, type=edge_type, provenance=provenance, confidence=confidence)

    def neighbors(
        self,
        node: str,
        edge_types: Iterable[str] | None = None,
        min_confidence: float = 0.0,
        direction: str = "both",
    ) -> list[tuple[str, dict[str, Any], str]]:
        """Return ``(neighbor_id, edge_attrs, direction)`` for a node."""
        allowed = set(edge_types) if edge_types else None
        out: list[tuple[str, dict[str, Any], str]] = []
        if direction in ("both", "out"):
            for _, t, d in self.graph.out_edges(node, data=True):
                if (allowed is None or d.get("type") in allowed) and d.get("confidence", 0) >= min_confidence:
                    out.append((t, d, "out"))
        if direction in ("both", "in"):
            for s, _, d in self.graph.in_edges(node, data=True):
                if (allowed is None or d.get("type") in allowed) and d.get("confidence", 0) >= min_confidence:
                    out.append((s, d, "in"))
        return out

    def expand(
        self,
        seeds: Iterable[str],
        depth: int = 1,
        budget: int = 25,
        edge_types: Iterable[str] | None = None,
        min_confidence: float = 0.30,
        exclude: Iterable[str] = (),
    ) -> list[ExpansionRecord]:
        """Breadth-first, budgeted, explainable expansion from ``seeds``.

        Deterministic: neighbors are visited in sorted order; ties broken by
        (hop, edge confidence desc, node id).
        """
        excluded = set(exclude)
        seeds = [s for s in seeds if s in self.graph]
        visited: set[str] = set(seeds) | excluded
        records: list[ExpansionRecord] = []
        # queue entries: (node, seed_origin, hop)
        q: deque[tuple[str, str, int]] = deque((s, s, 0) for s in sorted(seeds))
        while q and len(records) < budget:
            node, seed, hop = q.popleft()
            if hop >= depth:
                continue
            nbrs = self.neighbors(node, edge_types=edge_types, min_confidence=min_confidence)
            nbrs.sort(key=lambda t: (-t[1].get("confidence", 0.0), t[0], t[2]))
            for nbr, data, direction in nbrs:
                if nbr in visited:
                    continue
                visited.add(nbr)
                records.append(ExpansionRecord(
                    node=nbr, seed=seed, edge_type=data.get("type", "?"),
                    provenance=data.get("provenance", "?"),
                    confidence=float(data.get("confidence", 0.0)),
                    hop=hop + 1, direction=direction,
                ))
                q.append((nbr, seed, hop + 1))
                if len(records) >= budget:
                    break
        return records

    # ------------------------------------------------------------------ #
    # serialization / stats
    # ------------------------------------------------------------------ #
    def to_json(self, path: str | Path) -> None:
        payload = {
            "directed": True,
            "multigraph": True,
            "nodes": [
                {"id": n, "kind": d.get("kind"), "name": d.get("name"), "file": d.get("file")}
                for n, d in self.graph.nodes(data=True)
            ],
            "edges": [
                {"source": u, "target": v, "type": d.get("type"),
                 "provenance": d.get("provenance"), "confidence": d.get("confidence")}
                for u, v, d in self.graph.edges(data=True)
            ],
            "stats": self.stats(),
        }
        Path(path).write_text(json.dumps(payload, indent=1), encoding="utf-8")

    def stats(self) -> dict[str, Any]:
        edge_types: dict[str, int] = {}
        provs: dict[str, int] = {}
        for _, _, d in self.graph.edges(data=True):
            edge_types[d.get("type", "?")] = edge_types.get(d.get("type", "?"), 0) + 1
            provs[d.get("provenance", "?")] = provs.get(d.get("provenance", "?"), 0) + 1
        kinds: dict[str, int] = {}
        async_fn = 0
        for n, d in self.graph.nodes(data=True):
            kinds[d.get("kind", "?")] = kinds.get(d.get("kind", "?"), 0) + 1
            e = self.entities.get(n)
            if e is not None and e.is_async:
                async_fn += 1
        return {
            "num_nodes": self.graph.number_of_nodes(),
            "num_edges": self.graph.number_of_edges(),
            "node_kinds": kinds,
            "edge_types": edge_types,
            "provenance": provs,
            "async_functions": async_fn,
            "resolution": dict(self.resolution_stats),
        }


# --------------------------------------------------------------------------- #
# Construction
# --------------------------------------------------------------------------- #
def build_graph(parsed: ParsedRepository, config: GraphConfig | None = None) -> CodeGraph:
    config = config or GraphConfig()
    g = CodeGraph()
    enabled = set(config.enabled_edge_types)

    for ent in parsed.entities.values():
        g.add_entity(ent)

    # ---- structural containment ------------------------------------- #
    if "contains" in enabled:
        for ent in parsed.entities.values():
            if ent.kind == "module":
                continue
            if ent.kind == "file":
                g.add_edge(ent.id, f"module:{ent.file}", "contains", "ast_contains", 1.0)
            elif ent.parent:
                g.add_edge(ent.parent, ent.id, "contains", "ast_contains", 1.0)

    # ---- index definitions ------------------------------------------ #
    defs_by_simple: dict[str, list[str]] = {}
    module_defs: dict[str, dict[str, str]] = {}
    class_methods: dict[str, dict[str, str]] = {}
    class_of_method: dict[str, str] = {}
    for ent in parsed.entities.values():
        if ent.kind in ("class", "function"):
            defs_by_simple.setdefault(ent.name, []).append(ent.id)
            module_defs.setdefault(ent.file, {})[ent.name] = ent.id
        elif ent.kind == "method":
            defs_by_simple.setdefault(ent.name, []).append(ent.id)
            if ent.parent:
                class_methods.setdefault(ent.parent, {})[ent.name] = ent.id
                class_of_method[ent.id] = ent.parent

    # ---- imports ----------------------------------------------------- #
    imported_names: dict[str, dict[str, str]] = {}
    imported_modules: dict[str, dict[str, str]] = {}
    unresolved_imports = 0
    if "imports" in enabled:
        for imp in parsed.imports:
            if imp.is_from:
                target_rel = parsed.module_files.get(imp.module_name)
                # relative imports (level > 0) are approximated from the package of the importer
                if target_rel is None and imp.level > 0:
                    pkg = imp.importer_file.rsplit("/", 1)[0] if "/" in imp.importer_file else ""
                    parts = pkg.split("/") if pkg else []
                    parts = parts[: len(parts) - (imp.level - 1)] if imp.level > 1 else parts
                    cand = ".".join([*parts, imp.module_name]).strip(".")
                    target_rel = parsed.module_files.get(cand)
                if target_rel is None:
                    unresolved_imports += 1
                    continue
                g.add_edge(imp.importer, f"module:{target_rel}", "imports", "ast_import", 1.0)
                for nm in imp.names:
                    if nm == "*":
                        continue
                    tgt = module_defs.get(target_rel, {}).get(nm)
                    if tgt:
                        imported_names.setdefault(imp.importer_file, {})[nm] = tgt
            else:
                target_rel = parsed.module_files.get(imp.module_name)
                if target_rel is None:
                    unresolved_imports += 1
                    continue
                g.add_edge(imp.importer, f"module:{target_rel}", "imports", "ast_import", 0.8)
                top = imp.module_name.split(".")[0]
                imported_modules.setdefault(imp.importer_file, {})[top] = f"module:{target_rel}"

    # ---- calls ------------------------------------------------------- #
    resolved = heuristic = unresolved_calls = 0
    for call in parsed.calls:
        target: str | None = None
        conf = 0.0
        prov = "ast_call"
        rel = call.caller_file
        if call.attr_base is None:
            if call.name in imported_names.get(rel, {}):
                target, conf = imported_names[rel][call.name], 0.9
            elif call.name in module_defs.get(rel, {}):
                target, conf = module_defs[rel][call.name], 0.9
            elif call.name in defs_by_simple and len(defs_by_simple[call.name]) == 1:
                target, conf = defs_by_simple[call.name][0], 0.5
        elif call.attr_base in ("self", "cls"):
            cls = call.enclosing_class
            if cls and call.name in class_methods.get(cls, {}):
                target, conf = class_methods[cls][call.name], 0.8
        else:
            base = call.attr_base
            if base in imported_names.get(rel, {}):
                cls = imported_names[rel][base]
                if call.name in class_methods.get(cls, {}):
                    target, conf = class_methods[cls][call.name], 0.7
            elif base in imported_modules.get(rel, {}):
                mod_rel = imported_modules[rel][base].split(":", 1)[1]
                if call.name in module_defs.get(mod_rel, {}):
                    target, conf = module_defs[mod_rel][call.name], 0.6
        if target is None and config.enable_heuristic_calls:
            if call.name in defs_by_simple and len(defs_by_simple[call.name]) == 1:
                target, conf, prov = defs_by_simple[call.name][0], config.heuristic_call_confidence, "name_heuristic"
        if target is None:
            unresolved_calls += 1
            continue
        if conf < config.min_confidence:
            continue
        g.add_edge(call.caller, target, "calls", prov, conf)
        if prov == "name_heuristic":
            heuristic += 1
        else:
            resolved += 1

    # ---- references -------------------------------------------------- #
    unresolved_refs = 0
    if "references" in enabled:
        added: set[tuple[str, str]] = set()
        for ref in parsed.references:
            rel = ref.scope_file
            tgt = imported_names.get(rel, {}).get(ref.name)
            if tgt is None:
                cand = module_defs.get(rel, {}).get(ref.name)
                if cand is not None and (ref.name[:1].isupper() or ref.name.isupper()):
                    tgt = cand
            if tgt is None or (ref.scope, tgt) in added:
                if tgt is None:
                    unresolved_refs += 1
                continue
            added.add((ref.scope, tgt))
            g.add_edge(ref.scope, tgt, "references", "ast_reference", 0.6)

    g.resolution_stats = {
        "resolved_calls": resolved,
        "heuristic_calls": heuristic,
        "unresolved_calls": unresolved_calls,
        "unresolved_imports": unresolved_imports,
        "unresolved_references": unresolved_refs,
        "definitions": len(defs_by_simple),
    }
    return g
