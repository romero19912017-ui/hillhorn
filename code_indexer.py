# -*- coding: utf-8 -*-
"""Code indexer: scan project, extract blocks, build embeddings, search."""

from __future__ import annotations

import ast
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
CODE_INDEX_PATH = Path(os.getenv("CODE_INDEX_PATH", str(ROOT / "data" / "code_index")))

DEFAULT_IGNORE = [
    "node_modules", "venv", "__pycache__", ".git", "dist", "build",
    ".next", "target", ".venv", "venv_hillhorn",
]
CODE_EXT = (".py", ".ts", ".tsx", ".js", ".jsx")


def _should_ignore(path: Path, base: Path) -> bool:
    rel = path.relative_to(base) if base in path.parents or path == base else path
    parts = rel.parts
    for p in parts:
        if p in DEFAULT_IGNORE:
            return True
        if p.startswith(".") and p != ".git":
            return True
    return False


def _parse_python_blocks(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Extract functions and classes from Python via ast."""
    blocks = []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = node.lineno
                end = node.end_lineno or start
                snippet = "\n".join(content.splitlines()[start - 1:end])[:2000]
                name = node.name
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                blocks.append({
                    "file": file_path, "name": name, "kind": kind,
                    "start_line": start, "end_line": end, "snippet": snippet,
                })
    except SyntaxError:
        pass
    return blocks


def _parse_js_blocks(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Extract functions and classes via regex (JS/TS)."""
    blocks = []
    patterns = [
        (r"function\s+(\w+)\s*\(", "function"),
        (r"(\w+)\s*=\s*(?:async\s+)?function", "function"),
        (r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>", "function"),
        (r"class\s+(\w+)(?:\s+extends\s+\w+)?\s*\{", "class"),
    ]
    lines = content.splitlines()
    for i, line in enumerate(lines):
        for pat, kind in patterns:
            m = re.search(pat, line)
            if m:
                name = m.group(1)
                snippet = "\n".join(lines[max(0, i):min(len(lines), i + 30)])[:2000]
                blocks.append({
                    "file": file_path, "name": name, "kind": kind,
                    "start_line": i + 1, "end_line": min(i + 30, len(lines)),
                    "snippet": snippet,
                })
    return blocks


def _extract_blocks(path: Path, content: str, rel_path: str) -> List[Dict[str, Any]]:
    if path.suffix == ".py":
        return _parse_python_blocks(content, rel_path)
    return _parse_js_blocks(content, rel_path)


class CodeIndexer:
    """Index codebase for semantic search."""

    def __init__(
        self,
        workspace_path: Path,
        index_path: Optional[Path] = None,
    ):
        self.workspace_path = Path(workspace_path).resolve()
        self.index_path = Path(index_path or CODE_INDEX_PATH).resolve()
        self._field = None
        self._file_to_ids: Dict[str, List[str]] = {}

    def _load_field(self):
        from nwf import Field
        self.index_path.mkdir(parents=True, exist_ok=True)
        self._field = Field()
        if (self.index_path / "meta.json").exists():
            try:
                self._field.load(self.index_path)
            except Exception:
                pass
        self._rebuild_file_map()

    def _rebuild_file_map(self):
        self._file_to_ids = {}
        if self._field is None:
            return
        labels = self._field.get_labels()
        ids = self._field.get_ids() if hasattr(self._field, "get_ids") else []
        for i, lab in enumerate(labels):
            if isinstance(lab, dict) and "file" in lab:
                f = lab["file"]
                if f not in self._file_to_ids:
                    self._file_to_ids[f] = []
                idx = ids[i] if i < len(ids) else str(i)
                self._file_to_ids[f].append(idx)

    def _get_text_for_embedding(self, block: Dict[str, Any]) -> str:
        return f"file:{block['file']}\nname:{block['name']}\nkind:{block['kind']}\n\n{block['snippet']}"

    def index_file(self, path: Path) -> int:
        """Index single file. Returns count of blocks added."""
        rel = path.relative_to(self.workspace_path)
        rel_str = str(rel).replace("\\", "/")
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return 0
        blocks = _extract_blocks(path, content, rel_str)
        if not blocks:
            return 0
        from nwf import Charge, Field
        from embeddings import get_embedding
        import numpy as np

        if self._field is None:
            self._load_field()
        if self._field is None:
            self._field = Field()

        # Remove old charges for this file
        if rel_str in self._file_to_ids:
            # nwf Field may not have remove; we rebuild by excluding this file
            self._remove_file_from_index(rel_str)

        added = 0
        for block in blocks:
            text = self._get_text_for_embedding(block)
            z = get_embedding(text)
            if len(z.shape) == 0:
                z = np.array([z], dtype=np.float64)
            if z.shape[0] != 32:
                z = z[:32] if z.shape[0] >= 32 else np.pad(z, (0, 32 - z.shape[0]))
            sigma = np.full(32, 0.2, dtype=np.float64)
            charge = Charge(z=z.astype(np.float64), sigma=sigma, alpha=1.0)
            label = {k: v for k, v in block.items()}
            cid = f"{rel_str}:{block['name']}:{block['start_line']}"
            self._field.add(charge, labels=[label], ids=[cid])
            added += 1
        self._field.save(self.index_path)
        self._rebuild_file_map()
        return added

    def _remove_file_from_index(self, rel_str: str) -> None:
        """Remove all charges for given file from index."""
        ids = self._file_to_ids.get(rel_str, [])
        if ids and hasattr(self._field, "remove"):
            self._field.remove(ids)
            self._field.save(self.index_path)
        self._rebuild_file_map()

    def index_workspace(self) -> int:
        """Index entire workspace. Returns total blocks indexed."""
        total = 0
        for path in self.workspace_path.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in CODE_EXT:
                continue
            try:
                if _should_ignore(path, self.workspace_path):
                    continue
            except ValueError:
                continue
            total += self.index_file(path)
        return total

    def search_code(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """Semantic search over indexed code."""
        if self._field is None:
            self._load_field()
        if self._field is None or len(self._field) == 0:
            return []
        from embeddings import get_embedding
        import numpy as np

        qz = get_embedding(query)
        if qz.shape[0] != 32:
            qz = qz[:32] if qz.shape[0] >= 32 else np.pad(qz, (0, 32 - qz.shape[0]))
        charges = self._field.get_charges()
        labels = self._field.get_labels()
        z_all = np.stack([c.z for c in charges], axis=0)
        if z_all.shape[1] != qz.shape[0]:
            return []
        d = np.linalg.norm(z_all - qz, axis=1)
        idx = np.argsort(d)[:min(k, len(charges))]
        results = []
        for i in idx:
            lab = labels[int(i)]
            if isinstance(lab, dict):
                results.append({
                    "file": lab.get("file", ""),
                    "name": lab.get("name", ""),
                    "kind": lab.get("kind", ""),
                    "start_line": lab.get("start_line", 0),
                    "snippet": (lab.get("snippet", ""))[:500],
                })
        return results


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=None, help="Workspace path")
    parser.add_argument("--watch", action="store_true", help="Watch for changes")
    parser.add_argument("--index-path", default=None, help="Index storage path")
    args = parser.parse_args()
    workspace = Path(args.workspace or os.getenv("MOLTBOT_WORKSPACE", str(ROOT / "workspace")))
    indexer = CodeIndexer(workspace, args.index_path)

    if args.watch:
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            print("Install watchdog: pip install watchdog")
            sys.exit(1)
        debounce_sec = 2.0
        last_event = [0.0]
        pending = [None]

        class Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.is_directory:
                    return
                p = Path(event.src_path)
                if p.suffix not in CODE_EXT:
                    return
                try:
                    p.relative_to(workspace)
                except ValueError:
                    return
                pending[0] = p
                last_event[0] = time.time()

        observer = Observer()
        observer.schedule(Handler(), str(workspace), recursive=True)
        observer.start()
        print(f"Watching {workspace}")
        try:
            while True:
                time.sleep(0.5)
                if pending[0] and (time.time() - last_event[0]) >= debounce_sec:
                    p = pending[0]
                    pending[0] = None
                    if p.exists():
                        n = indexer.index_file(p)
                        print(f"Indexed {p.name}: {n} blocks")
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
    else:
        n = indexer.index_workspace()
        print(f"Indexed {n} blocks")


if __name__ == "__main__":
    main()
