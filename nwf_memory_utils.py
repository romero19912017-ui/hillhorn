# -*- coding: utf-8 -*-
"""NWF memory utilities: pruning, export, import."""

from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent
NWF_MEMORY_PATH = Path(__file__).resolve().parent / "data" / "deepseek_memory"


def prune_field(
    field_path: Optional[Path] = None,
    max_charges: int = 10000,
    max_age_days: float = 90.0,
    min_alpha: float = 0.05,
) -> int:
    """Remove old/low-priority charges. Returns number of charges removed."""
    import os
    fp = field_path or Path(os.getenv("NWF_MEMORY_PATH", str(ROOT / "data" / "deepseek_memory")))
    if not (fp / "meta.json").exists():
        return 0
    try:
        from nwf import Field
        field = Field()
        field.load(fp)
        charges = field.get_charges()
        labels = field.get_labels()
        if len(charges) <= max_charges:
            return 0
        now = time.time()
        max_age_sec = max_age_days * 86400
        scored: List[tuple] = []
        for i, (c, lab) in enumerate(zip(charges, labels)):
            ts = lab.get("timestamp", now) if isinstance(lab, dict) else now
            alpha = getattr(c, "alpha", 1.0)
            age = now - (ts if isinstance(ts, (int, float)) else now)
            if age > max_age_sec or alpha < min_alpha:
                continue
            scored.append((ts, alpha, c, lab if isinstance(lab, dict) else {}))
        scored.sort(key=lambda x: (-x[0], -x[1]))
        keep = scored[:max_charges]
        if len(keep) >= len(charges):
            return 0
        new_field = Field()
        for i, (_, _, c, lab) in enumerate(keep):
            new_field.add(c, labels=[lab], ids=[f"pruned_{i}"])
        new_field.save(fp)
        return len(charges) - len(keep)
    except Exception:
        return 0


def export_field(field_path: Optional[Path] = None, out_path: Optional[Path] = None) -> bool:
    """Export NWF field to file (copy directory)."""
    import shutil
    import os
    fp = field_path or Path(os.getenv("NWF_MEMORY_PATH", str(ROOT / "data" / "deepseek_memory")))
    out = out_path or fp.parent / f"{fp.name}_export_{int(time.time())}"
    if not fp.exists():
        return False
    try:
        shutil.copytree(fp, out, dirs_exist_ok=True)
        return True
    except Exception:
        return False


def import_field(src_path: Path, dest_path: Optional[Path] = None) -> bool:
    """Import NWF field from path. Replaces dest."""
    import shutil
    import os
    dest = dest_path or Path(os.getenv("NWF_MEMORY_PATH", str(ROOT / "data" / "deepseek_memory")))
    if not src_path.exists():
        return False
    try:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src_path, dest)
        return True
    except Exception:
        return False
