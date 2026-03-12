# -*- coding: utf-8 -*-
"""NWF Memory Adapter: синхронизация Markdown-памяти OpenCloud/Moltbot с полем NWF."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from nwf import Charge, Field

# -----------------------------------------------------------------------------
# Конфигурация
# -----------------------------------------------------------------------------

MOLTBOT_WORKSPACE = Path(
    os.getenv("MOLTBOT_WORKSPACE", os.path.expanduser("~/.openclaw/workspace"))
)
NWF_FIELD_PATH = Path(os.getenv("NWF_MEMORY_ADAPTER_PATH", "data/nwf_opencloud"))
EMBED_DIM = 32
MEMORY_FILES = ["SOUL.md", "USER.md", "MEMORY.md"]
MEMORY_DIR = "memory"

# Optional: Hugging Face for semantic embeddings (set HF_TOKEN in .env)
HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL = os.getenv("HF_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# -----------------------------------------------------------------------------
# Эмбеддинги: hash или Hugging Face (если HF_TOKEN задан)
# -----------------------------------------------------------------------------


def _hash_embedding(text: str, dim: int = EMBED_DIM) -> np.ndarray:
    """Детерминированный эмбеддинг на основе SHA256."""
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    np.random.seed(int(h[:8], 16) % (2**32))
    return np.random.randn(dim).astype(np.float64) * 0.1


def _hf_embedding(text: str, dim: int = 384) -> Optional[np.ndarray]:
    """Семантический эмбеддинг через sentence-transformers (опционально)."""
    try:
        from sentence_transformers import SentenceTransformer
        token = HF_TOKEN or os.getenv("HF_TOKEN") or None
        model = SentenceTransformer(HF_MODEL, token=token)
        emb = model.encode(text, convert_to_numpy=True)
        if emb.shape[0] != dim:
            emb = np.pad(emb, (0, max(0, dim - emb.shape[0])))[:dim]
        return emb.astype(np.float64)
    except Exception:
        return None


def get_embedding(text: str, dim: int = EMBED_DIM) -> np.ndarray:
    """Получить эмбеддинг: HF если доступен, иначе hash. Всегда возвращает shape (dim,)."""
    emb = _hf_embedding(text, dim=384)
    if emb is not None:
        if len(emb) > dim:
            emb = emb[:dim]
        elif len(emb) < dim:
            emb = np.pad(emb, (0, dim - len(emb)))
        return emb.astype(np.float64)
    return _hash_embedding(text, dim)

# -----------------------------------------------------------------------------
# Парсинг Markdown: разбиение на блоки по заголовкам
# -----------------------------------------------------------------------------


def split_md_blocks(content: str) -> List[str]:
    """Разбить Markdown на семантические блоки (заголовок + содержимое)."""
    blocks = []
    current = []
    for line in content.split("\n"):
        if re.match(r"^#+\s", line):
            if current:
                blocks.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return [b for b in blocks if len(b) > 10]


def collect_memory_blocks(workspace: Path) -> List[Dict[str, Any]]:
    """Собрать блоки из SOUL.md, USER.md, MEMORY.md и memory/*.md."""
    blocks = []
    for name in MEMORY_FILES:
        p = workspace / name
        if p.exists():
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                for i, b in enumerate(split_md_blocks(text)):
                    blocks.append({
                        "source": name,
                        "block_index": i,
                        "text": b,
                        "file_path": str(p),
                    })
            except Exception:
                pass
    mem_dir = workspace / MEMORY_DIR
    if mem_dir.exists():
        for f in sorted(mem_dir.glob("*.md")):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
                for i, b in enumerate(split_md_blocks(text)):
                    blocks.append({
                        "source": f"memory/{f.name}",
                        "block_index": i,
                        "text": b,
                        "file_path": str(f),
                    })
            except Exception:
                pass
    return blocks

# -----------------------------------------------------------------------------
# Синхронизация с NWF-полем
# -----------------------------------------------------------------------------


def blocks_to_charges(blocks: List[Dict[str, Any]]) -> List[Charge]:
    """Преобразовать блоки в NWF Charges (заряды)."""
    charges = []
    for blk in blocks:
        text = blk.get("text", "")
        if not text:
            continue
        z = get_embedding(text)
        sigma = np.full(EMBED_DIM, 0.2, dtype=np.float64)
        alpha = 1.5 if blk.get("source") == "MEMORY.md" else 1.0
        charges.append(Charge(z=z, sigma=sigma, alpha=alpha))
    return charges


def sync_workspace_to_nwf(
    workspace: Optional[Path] = None,
    field_path: Optional[Path] = None,
) -> int:
    """
    Синхронизировать Markdown рабочей области Moltbot/OpenCloud с NWF-полем (полная замена).
    Возвращает количество записанных зарядов.
    """
    ws = workspace or MOLTBOT_WORKSPACE
    fp = field_path or NWF_FIELD_PATH
    if not ws.exists():
        return 0
    blocks = collect_memory_blocks(ws)
    charges = blocks_to_charges(blocks)
    if not charges:
        return 0
    fp.mkdir(parents=True, exist_ok=True)
    field = Field()
    for i, (c, blk) in enumerate(zip(charges, blocks)):
        field.add(c, labels=[blk], ids=[f"{blk['source']}_{blk['block_index']}_{i}"])
    field.save(fp)
    return len(charges)


def search_similar(query: str, k: int = 5, field_path: Optional[Path] = None) -> List[Dict]:
    """Поиск похожих блоков памяти в NWF-поле."""
    fp = field_path or NWF_FIELD_PATH
    if not (fp / "meta.json").exists():
        return []
    field = Field()
    field.load(fp)
    if len(field) == 0:
        return []
    qz = get_embedding(query)
    charges = field.get_charges()
    labels = field.get_labels()
    z_all = np.stack([c.z for c in charges], axis=0)
    d = np.linalg.norm(qz - z_all, axis=1)
    idx = np.argsort(d)[:k]
    return [
        {"text": labels[i].get("text", "")[:300], "source": labels[i].get("source", "")}
        for i in idx
        if isinstance(labels[i], dict)
    ]


def run_watch(workspace: Optional[Path] = None, field_path: Optional[Path] = None) -> None:
    """Отслеживать изменения .md в workspace и синхронизировать с NWF."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("Install watchdog: pip install watchdog")
        return
    ws = Path(workspace) if workspace else MOLTBOT_WORKSPACE
    if not ws.exists():
        print(f"Workspace not found: {ws}")
        return

    class SyncHandler(FileSystemEventHandler):
        def __init__(self, base: Path, fp: Path):
            self.base = base
            self.fp = fp
            self._debounce = 0.0
            import time
            self._last = time.time()

        def on_modified(self, event):
            if event.is_directory:
                return
            if event.src_path.endswith(".md"):
                import time
                now = time.time()
                if now - self._last < 1.0:
                    return
                self._last = now
                n = sync_workspace_to_nwf(workspace=self.base, field_path=self.fp)
                print(f"[watch] Synced {n} blocks")

    fp = field_path or NWF_FIELD_PATH
    handler = SyncHandler(ws, fp)
    observer = Observer()
    observer.schedule(handler, str(ws), recursive=True)
    observer.start()
    print(f"Watching {ws} -> {fp}. Ctrl+C to stop.")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="NWF Memory Adapter for OpenCloud/Moltbot")
    p.add_argument("--sync", action="store_true", help="Sync workspace to NWF")
    p.add_argument("--watch", action="store_true", help="Watch workspace and auto-sync on .md changes")
    p.add_argument("--search", type=str, help="Search similar memories")
    p.add_argument("--workspace", type=str, default=None)
    p.add_argument("-k", type=int, default=5)
    args = p.parse_args()
    if args.search:
        for r in search_similar(args.search, k=args.k):
            print("---")
            print(r.get("source", ""), ":", r.get("text", "")[:200])
    elif args.watch:
        ws = Path(args.workspace) if args.workspace else MOLTBOT_WORKSPACE
        run_watch(workspace=ws)
    elif args.sync:
        ws = Path(args.workspace) if args.workspace else None
        n = sync_workspace_to_nwf(workspace=ws)
        print(f"Synced {n} blocks to NWF")
    else:
        p.print_help()


if __name__ == "__main__":
    main()
