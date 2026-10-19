"""Repository traversal and Python AST entity extraction.

The parser is deliberately conservative: every relationship it emits carries a
*provenance* label so downstream consumers can tell statically verified structure
(``ast_import``, ``ast_contains``, ``ast_defines``) apart from heuristics
(``name_heuristic``).

Only Python is parsed in this version; other languages can be added by extending
``parse_file`` and the suffix list in :class:`~repoclosure.config.ParseConfig`.
"""
from __future__ import annotations

import ast
import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

from .config import ParseConfig


# --------------------------------------------------------------------------- #
# Data types
# --------------------------------------------------------------------------- #
@dataclass
class Entity:
    """A retrievable code entity."""

    id: str
    kind: str  # file | module | class | function | method
    name: str
    qualname: str
    file: str  # repository-relative path
    module: str  # dotted module name derived from the path
    start_line: int
    end_line: int
    docstring: str = ""
    is_async: bool = False
    parent: str | None = None
    signature: str = ""
    source: str = ""
    content_hash: str = ""

    def search_text(self, max_chars: int = 2000) -> str:
        """Text representation used for lexical and semantic indexing."""
        parts = [self.qualname, self.file]
        if self.signature:
            parts.append(self.signature)
        if self.docstring:
            parts.append(self.docstring)
        if self.source:
            parts.append(self.source[:max_chars])
        return "\n".join(p for p in parts if p)


@dataclass
class ImportRecord:
    importer: str  # node id of the importing module
    importer_file: str
    module_name: str  # dotted module as written (best effort absolute)
    names: list[str]  # imported names ("*" for star imports)
    level: int
    lineno: int
    is_from: bool


@dataclass
class CallRecord:
    caller: str  # node id
    caller_file: str
    enclosing_class: str | None
    name: str  # simple call name
    attr_base: str | None  # e.g. "self", "requests", "obj"
    lineno: int


@dataclass
class ReferenceRecord:
    scope: str  # node id
    scope_file: str
    name: str
    lineno: int


@dataclass
class ParseError:
    file: str
    error_type: str
    message: str


@dataclass
class ParsedRepository:
    entities: dict[str, Entity] = field(default_factory=dict)
    imports: list[ImportRecord] = field(default_factory=list)
    calls: list[CallRecord] = field(default_factory=list)
    references: list[ReferenceRecord] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)
    file_hashes: dict[str, str] = field(default_factory=dict)
    module_files: dict[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Traversal
# --------------------------------------------------------------------------- #
def walk_repository(root: str | Path, config: ParseConfig | None = None) -> list[str]:
    """Return sorted repository-relative paths of parseable source files."""
    config = config or ParseConfig()
    root = Path(root)
    ignored = set(config.ignored_dirs)
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in ignored and not d.startswith("."))
        for fn in sorted(filenames):
            if not fn.endswith(tuple(config.source_suffixes)):
                continue
            full = Path(dirpath) / fn
            rel = full.relative_to(root).as_posix()
            if any(part in rel for part in config.ignored_path_parts):
                continue
            try:
                if full.stat().st_size > config.max_file_bytes:
                    continue
            except OSError:
                continue
            out.append(rel)
    return sorted(out)


def _module_name(rel_path: str) -> str:
    p = rel_path[:-3] if rel_path.endswith(".py") else rel_path
    if p.endswith("/__init__"):
        p = p[: -len("/__init__")]
    elif p == "__init__":
        p = ""
    return p.replace("/", ".")


def _safe_read(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:4096]:
        return None  # binary
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return data.decode("latin-1")
        except Exception:  # pragma: no cover
            return None


def _signature(node: ast.AST) -> str:
    try:
        return ast.unparse(node.args)  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover
        return ""


# --------------------------------------------------------------------------- #
# Per-file parsing
# --------------------------------------------------------------------------- #
def parse_file(rel_path: str, source: str) -> tuple[
    list[Entity], list[ImportRecord], list[CallRecord], list[ReferenceRecord], ParseError | None
]:
    module = _module_name(rel_path)
    lines = source.splitlines()
    content_hash = hashlib.sha256(source.encode("utf-8", "replace")).hexdigest()

    module_id = f"module:{rel_path}"
    file_id = f"file:{rel_path}"
    module_entity = Entity(
        id=module_id, kind="module", name=module or rel_path, qualname=module or rel_path,
        file=rel_path, module=module, start_line=1, end_line=max(1, len(lines)),
        content_hash=content_hash,
    )
    file_entity = Entity(
        id=file_id, kind="file", name=Path(rel_path).name, qualname=rel_path,
        file=rel_path, module=module, start_line=1, end_line=max(1, len(lines)),
        source="\n".join(lines[:80]), content_hash=content_hash,
    )

    try:
        tree = ast.parse(source, filename=rel_path)
    except SyntaxError as exc:
        return [file_entity, module_entity], [], [], [], ParseError(
            rel_path, "SyntaxError", f"{exc.msg} (line {exc.lineno})"
        )
    except (ValueError, RecursionError) as exc:  # malformed / pathological input
        return [file_entity, module_entity], [], [], [], ParseError(
            rel_path, type(exc).__name__, str(exc)
        )

    entities: list[Entity] = [file_entity, module_entity]
    imports: list[ImportRecord] = []
    calls: list[CallRecord] = []
    references: list[ReferenceRecord] = []

    def seg(node: ast.AST) -> str:
        start = getattr(node, "lineno", 1)
        end = getattr(node, "end_lineno", start) or start
        return "\n".join(lines[start - 1:end])

    def docstring(node: ast.AST) -> str:
        return ast.get_docstring(node) or ""  # type: ignore[arg-type]

    def make_id(kind: str, qualname: str) -> str:
        return f"{kind}:{rel_path}:{qualname}"

    def visit_imports(node: ast.AST) -> None:
        for child in ast.walk(node):
            if isinstance(child, ast.Import):
                for alias in child.names:
                    imports.append(ImportRecord(
                        importer=module_id, importer_file=rel_path, module_name=alias.name,
                        names=["*"], level=0, lineno=child.lineno, is_from=False,
                    ))
            elif isinstance(child, ast.ImportFrom):
                base = child.module or ""
                names = [a.name for a in child.names]
                imports.append(ImportRecord(
                    importer=module_id, importer_file=rel_path, module_name=base, names=names,
                    level=child.level or 0, lineno=child.lineno, is_from=True,
                ))

    def collect_scope(node: ast.AST, scope_id: str, scope_file: str, enclosing_class: str | None) -> None:
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                fn = child.func
                if isinstance(fn, ast.Name):
                    calls.append(CallRecord(scope_id, scope_file, enclosing_class, fn.id, None, child.lineno))
                elif isinstance(fn, ast.Attribute):
                    base = None
                    if isinstance(fn.value, ast.Name):
                        base = fn.value.id
                    calls.append(CallRecord(scope_id, scope_file, enclosing_class, fn.attr, base, child.lineno))
            elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                references.append(ReferenceRecord(scope_id, scope_file, child.id, child.lineno))

    def visit_body(body: list[ast.stmt], parent_id: str, parent_qual: str,
                   enclosing_class: str | None) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                qual = f"{parent_qual}.{node.name}" if parent_qual else node.name
                cid = make_id("class", qual)
                entities.append(Entity(
                    id=cid, kind="class", name=node.name, qualname=qual, file=rel_path,
                    module=module, start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno) or node.lineno,
                    docstring=docstring(node), parent=parent_id, content_hash=content_hash,
                ))
                for b in node.body:
                    if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        mqual = f"{qual}.{b.name}"
                        mid = make_id("method", mqual)
                        entities.append(Entity(
                            id=mid, kind="method", name=b.name, qualname=mqual, file=rel_path,
                            module=module, start_line=b.lineno,
                            end_line=getattr(b, "end_lineno", b.lineno) or b.lineno,
                            docstring=docstring(b), is_async=isinstance(b, ast.AsyncFunctionDef),
                            parent=cid, signature=_signature(b), source=seg(b),
                            content_hash=content_hash,
                        ))
                        collect_scope(b, mid, rel_path, cid)
                # nested classes
                visit_body([b for b in node.body if isinstance(b, ast.ClassDef)], cid, qual, cid)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = f"{parent_qual}.{node.name}" if parent_qual else node.name
                fid = make_id("function", qual)
                entities.append(Entity(
                    id=fid, kind="function", name=node.name, qualname=qual, file=rel_path,
                    module=module, start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno) or node.lineno,
                    docstring=docstring(node), is_async=isinstance(node, ast.AsyncFunctionDef),
                    parent=parent_id, signature=_signature(node), source=seg(node),
                    content_hash=content_hash,
                ))
                collect_scope(node, fid, rel_path, enclosing_class)
                visit_body([b for b in node.body if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))],
                           fid, qual, None)

    visit_imports(tree)
    visit_body(tree.body, module_id, "", None)

    return entities, imports, calls, references, None


# --------------------------------------------------------------------------- #
# Repository-level entry point
# --------------------------------------------------------------------------- #
def parse_repository(root: str | Path, config: ParseConfig | None = None) -> ParsedRepository:
    config = config or ParseConfig()
    root = Path(root)
    parsed = ParsedRepository()
    files = walk_repository(root, config)
    # First pass: module name -> file so that imports can be resolved.
    for rel in files:
        parsed.module_files[_module_name(rel)] = rel
    for rel in files:
        text = _safe_read(root / rel)
        if text is None:
            parsed.errors.append(ParseError(rel, "Unreadable", "could not decode file"))
            continue
        ents, imports, calls, refs, err = parse_file(rel, text)
        for e in ents:
            parsed.entities[e.id] = e
        parsed.imports.extend(imports)
        parsed.calls.extend(calls)
        parsed.references.extend(refs)
        parsed.file_hashes[rel] = ents[0].content_hash if ents else ""
        if err is not None:
            parsed.errors.append(err)
    return parsed
