"""Clone target repositories once and materialise each base_commit as a worktree.

Only repositories that appear in the curated benchmark whitelist are cloned. Each
clone lives under ``data/repos/<owner>__<name>/`` (git-ignored). Worktrees are created
under ``data/worktrees/<instance_id>/`` so that every benchmark instance is evaluated
against the exact frozen snapshot named by ``base_commit``.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_REPOS = [
    "psf/requests",
    "pallets/flask",
    "marshmallow-code/marshmallow",
    "mwaskom/seaborn",
    "pylint-dev/astroid",
    "sqlfluff/sqlfluff",
    "pydicom/pydicom",
    "pvlib/pvlib-python",
]


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)


def ensure_clone(full_name: str) -> Path:
    dest = ROOT / "data" / "repos" / full_name.replace("/", "__")
    if (dest / ".git").exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://github.com/{full_name}.git"
    print(f"cloning {full_name} -> {dest}")
    run(["git", "clone", "--quiet", url, str(dest)])
    return dest


def ensure_worktree(clone: Path, instance_id: str, base_commit: str) -> Path:
    dest = ROOT / "data" / "worktrees" / instance_id
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Make sure the commit object exists locally (clone has full history, so it should).
    res = run(["git", "cat-file", "-e", base_commit], cwd=clone, check=False)
    if res.returncode != 0:
        run(["git", "fetch", "--quiet", "origin", base_commit], cwd=clone, check=False)
    run(["git", "worktree", "add", "--detach", "--quiet", str(dest), base_commit], cwd=clone)
    return dest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", nargs="*", default=DEFAULT_REPOS)
    ap.add_argument("--benchmark", default=str(ROOT / "data" / "swebench_lite.json"))
    ap.add_argument("--out", default=str(ROOT / "benchmarks" / "repo_manifest.json"))
    args = ap.parse_args()

    data = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
    rows = data["splits"]["test"] + data["splits"]["dev"]
    wanted = [r for r in rows if r["repo"] in set(args.repos)]
    print(f"selected {len(wanted)} instances from {len(args.repos)} repos")

    manifest = []
    for repo in sorted(set(args.repos)):
        subset = [r for r in wanted if r["repo"] == repo]
        if not subset:
            print(f"  (no instances for {repo}; skipping)")
            continue
        try:
            clone = ensure_clone(repo)
        except subprocess.CalledProcessError as exc:
            print(f"  clone failed for {repo}: {exc.stderr.strip()[:200]}", file=sys.stderr)
            continue
        for r in subset:
            try:
                wt = ensure_worktree(clone, r["instance_id"], r["base_commit"])
                manifest.append({"instance_id": r["instance_id"], "repo": repo,
                                 "base_commit": r["base_commit"], "path": str(wt)})
                print(f"  ready {r['instance_id']}")
            except subprocess.CalledProcessError as exc:
                print(f"  worktree failed {r['instance_id']}: {exc.stderr.strip()[:150]}",
                      file=sys.stderr)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"repos": args.repos, "instances": manifest}, indent=1),
                              encoding="utf-8")
    print(f"wrote {args.out} ({len(manifest)} instances)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
