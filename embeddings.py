# -*- coding: utf-8 -*-
"""Unified embeddings for Hillhorn: hash (default) or sentence-transformers with projection."""

from __future__ import annotations

import hashlib
import os
from typing import Optional

import numpy as np

EMBED_DIM = 32
SEMANTIC_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SEMANTIC_DIM = 384

_encoder = None


def _hash_embedding(text: str, dim: int = EMBED_DIM) -> np.ndarray:
    """Deterministic hash-based embedding (matches legacy behavior)."""
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    np.random.seed(int(h[:8], 16) % (2**32))
    return np.random.randn(dim).astype(np.float64) * 0.1


def _project_384_to_32(vec: np.ndarray) -> np.ndarray:
    """Project 384-dim vector to 32 via mean pooling of consecutive chunks."""
    if vec.shape[0] != SEMANTIC_DIM:
        if vec.shape[0] >= EMBED_DIM:
            return vec[:EMBED_DIM].astype(np.float64)
        return np.pad(vec.astype(np.float64), (0, EMBED_DIM - vec.shape[0]))
    chunk = SEMANTIC_DIM // EMBED_DIM  # 12
    out = [vec[i * chunk:(i + 1) * chunk].mean() for i in range(EMBED_DIM)]
    return np.array(out, dtype=np.float64)


def _load_semantic_encoder():
    global _encoder
    if _encoder is not None:
        return _encoder
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _encoder = SentenceTransformer(SEMANTIC_MODEL)
        return _encoder
    except ImportError:
        return None


def get_embedding(text: str, dim: int = EMBED_DIM, use_semantic: Optional[bool] = None) -> np.ndarray:
    """
    Unified embedding: semantic (if available) with projection, else hash.
    use_semantic: None=from env USE_SEMANTIC_EMBEDDINGS, True/False override.
    """
    if use_semantic is None:
        env_val = os.getenv("USE_SEMANTIC_EMBEDDINGS", "").lower()
        use_semantic = env_val in ("1", "true", "yes")
    if not use_semantic:
        return _hash_embedding(text, dim)
    enc = _load_semantic_encoder()
    if enc is None:
        return _hash_embedding(text, dim)
    try:
        vec = enc.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        if vec.shape[0] == SEMANTIC_DIM and dim == EMBED_DIM:
            return _project_384_to_32(vec)
        if vec.shape[0] >= dim:
            return vec[:dim].astype(np.float64)
        return np.pad(vec.astype(np.float64), (0, dim - vec.shape[0]))
    except Exception:
        return _hash_embedding(text, dim)
