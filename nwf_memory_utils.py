# -*- coding: utf-8 -*-
"""Утилиты NWF-памяти: очистка (prune), экспорт, импорт."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent
_DATA_ROOT = Path(os.getenv("HILLHORN_DATA_ROOT", "C:/hillhorn_data"))
NWF_MEMORY_PATH = Path(os.getenv("NWF_MEMORY_PATH", str(_DATA_ROOT / "deepseek_memory")))


def prune_field(
    field_path: Optional[Path] = None,
    max_charges: int = 10000,
    max_age_days: float = 90.0,
    min_alpha: float = 0.05,
) -> int:
    """Удалить старые/низкоприоритетные заряды. Возвращает количество удалённых."""
    import os
    fp = field_path or Path(os.getenv("NWF_MEMORY_PATH", str(_DATA_ROOT / "deepseek_memory")))
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
    """Экспортировать NWF-поле в каталог (копирование)."""
    import shutil
    import os
    fp = field_path or Path(os.getenv("NWF_MEMORY_PATH", str(_DATA_ROOT / "deepseek_memory")))
    out = out_path or fp.parent / f"{fp.name}_export_{int(time.time())}"
    if not fp.exists():
        return False
    try:
        shutil.copytree(fp, out, dirs_exist_ok=True)
        return True
    except Exception:
        return False


def boost_charges_alpha(
    indices: List[int],
    delta: float = 0.1,
    max_alpha: float = 2.0,
    field_path: Optional[Path] = None,
) -> int:
    """
    Увеличить alpha для зарядов по индексам (успешное использование).
    При неудаче можно вызывать с delta < 0. Возвращает количество обновлённых зарядов.
    """
    fp = field_path or Path(os.getenv("NWF_MEMORY_PATH", str(_DATA_ROOT / "deepseek_memory")))
    if not (fp / "meta.json").exists():
        return 0
    try:
        from nwf import Charge, Field

        field = Field()
        field.load(fp)
        charges = field.get_charges()
        labels = field.get_labels()
        if not charges or not labels:
            return 0
        n_charges = len(charges)
        n_labels = len(labels)
        idx_set = frozenset(i for i in indices if 0 <= i < n_charges)
        if not idx_set:
            return 0
        new_field = Field()
        for i in range(n_charges):
            c = charges[i]
            lab = labels[i] if i < n_labels else {}
            alpha = getattr(c, "alpha", 1.0)
            if i in idx_set:
                alpha = min(max_alpha, max(0.05, alpha + delta))
            new_c = Charge(z=c.z, sigma=c.sigma, alpha=float(alpha))
            lab_list = [lab] if isinstance(lab, dict) else [{}]
            new_field.add(new_c, labels=lab_list, ids=[f"boost_{i}"])  # noqa: E501
        new_field.save(fp)
        return len(idx_set)
    except Exception:
        return 0


def import_field(src_path: Path, dest_path: Optional[Path] = None) -> bool:
    """Импортировать NWF-поле из пути. Заменяет dest."""
    import shutil
    import os
    dest = dest_path or Path(os.getenv("NWF_MEMORY_PATH", str(_DATA_ROOT / "deepseek_memory")))
    if not src_path.exists():
        return False
    try:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src_path, dest)
        return True
    except Exception:
        return False
