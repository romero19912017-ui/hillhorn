# -*- coding: utf-8 -*-
"""NWF-JEPA: Joint Embedding Predictive Architecture с полем NWF.

Архитектура: ContextEncoder, TargetEncoder (EMA), NWFPredictor (z, sigma, alpha).
Интеграция с nwf-core Field и FAISS для поиска похожих ситуаций.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn

from nwf import Charge, Field

try:
    from nwf.index_faiss import FAISSIndex
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    FAISSIndex = None

# -----------------------------------------------------------------------------
# NWFPredictor: выход (z, sigma, alpha) вместо точечного z
# -----------------------------------------------------------------------------


class NWFPredictor(nn.Module):
    """Предиктор с вероятностным выходом (z, sigma, alpha)."""

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
        super().__init__()
        self.output_dim = output_dim
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, output_dim * 3),
        )

    def forward(
        self, x: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        out = self.net(x)
        d = self.output_dim
        z = out[..., :d]
        log_sigma = out[..., d : 2 * d]
        sigma = torch.exp(torch.clamp(log_sigma, -10, 10)) + 1e-6
        alpha = torch.sigmoid(out[..., 2 * d :])
        return z, sigma, alpha


# -----------------------------------------------------------------------------
# ContextEncoder: преобразует вход в embedding
# -----------------------------------------------------------------------------


class ContextEncoder(nn.Module):
    """Контекстный энкодер. Поддерживает векторы или токены."""

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        num_regularization_tokens: int = 4,
    ):
        super().__init__()
        self.output_dim = output_dim
        self.num_reg_tokens = num_regularization_tokens
        self.proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, output_dim),
        )
        self.reg_tokens = nn.Parameter(torch.randn(1, num_regularization_tokens, output_dim) * 0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, seq_len, input_dim) или (B, input_dim)
        if x.dim() == 2:
            h = self.proj(x)
            reg = self.reg_tokens.expand(x.shape[0], -1, -1)
            out = torch.cat([h.unsqueeze(1), reg], dim=1)
            return out.mean(dim=1)
        h = self.proj(x)
        reg = self.reg_tokens.expand(x.shape[0], -1, -1)
        combined = torch.cat([h, reg], dim=1)
        return combined.mean(dim=1)


# -----------------------------------------------------------------------------
# TargetEncoder: EMA от контекстного энкодера
# -----------------------------------------------------------------------------


class TargetEncoder(nn.Module):
    """Таргет-энкодер с EMA обновлением весов от ContextEncoder."""

    def __init__(self, encoder: ContextEncoder, decay: float = 0.996):
        super().__init__()
        self.encoder = encoder
        self.decay = decay
        self.target = ContextEncoder(
            encoder.proj[0].in_features,
            encoder.proj[0].out_features,
            encoder.output_dim,
            encoder.num_reg_tokens,
        )
        self.target.load_state_dict(encoder.state_dict())

    @torch.no_grad()
    def update_ema(self) -> None:
        for p_t, p_s in zip(self.target.parameters(), self.encoder.parameters()):
            p_t.data.mul_(self.decay).add_(p_s.data, alpha=1 - self.decay)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.target(x)


# -----------------------------------------------------------------------------
# MemoryAwareJEPA: JEPA + NWF Field + FAISS
# -----------------------------------------------------------------------------


class MemoryAwareJEPA(nn.Module):
    """JEPA с памятью NWF и FAISS для поиска похожих ситуаций."""

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        embed_dim: int,
        ema_decay: float = 0.996,
        use_faiss: bool = True,
    ):
        super().__init__()
        self.embed_dim = embed_dim
        self.encoder = ContextEncoder(input_dim, hidden_dim, embed_dim)
        self.target_encoder = TargetEncoder(self.encoder, decay=ema_decay)
        self.predictor = NWFPredictor(embed_dim, hidden_dim, embed_dim)
        self.memory = Field()
        self.use_faiss = use_faiss
        self._faiss_index: Optional[FAISSIndex] = None
        self._mem_counter = 0

    def encode_context(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)

    def encode_target(self, x: torch.Tensor) -> torch.Tensor:
        return self.target_encoder(x)

    def predict(
        self,
        z_context: torch.Tensor,
        similar_charges: Optional[List[Charge]] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Предсказание (z, sigma, alpha) из контекста. Опционально: обогащение из памяти."""
        if similar_charges and len(similar_charges) > 0:
            # Усредняем похожие z как дополнительный контекст (простая схема)
            z_mem = np.stack([c.z for c in similar_charges], axis=0)
            z_mem = torch.from_numpy(z_mem).float().to(z_context.device)
            z_mem_mean = z_mem.mean(dim=0, keepdim=True).expand_as(z_context)
            z_input = 0.7 * z_context + 0.3 * z_mem_mean
        else:
            z_input = z_context
        return self.predictor(z_input)

    def retrieve_similar(
        self,
        query_z: Union[np.ndarray, torch.Tensor],
        k: int = 5,
    ) -> List[Charge]:
        """Поиск похожих зарядов в памяти по z (L2)."""
        if len(self.memory) == 0:
            return []
        q = np.asarray(query_z, dtype=np.float64)
        if q.ndim == 1:
            q = q.reshape(1, -1)
        charges = self.memory.get_charges()
        z_all = np.stack([c.z for c in charges], axis=0)
        dim = min(q.shape[1], z_all.shape[1])
        d = np.linalg.norm(q[:, :dim] - z_all[:, :dim], axis=1)
        idx = np.argsort(d)[: min(k, len(charges))]
        return [charges[int(i)] for i in idx]

    def add_to_memory(
        self,
        z: np.ndarray,
        sigma: np.ndarray,
        alpha: float = 1.0,
        label: Optional[any] = None,
    ) -> None:
        """Добавить заряд в память."""
        c = Charge(z=np.asarray(z, dtype=np.float64), sigma=np.asarray(sigma, dtype=np.float64), alpha=alpha)
        self.memory.add(c, labels=[label], ids=[self._mem_counter])
        self._mem_counter += 1
        self._faiss_index = None

    def build_faiss_index(self) -> None:
        """Перестроить FAISS индекс (для большого числа зарядов)."""
        if not HAS_FAISS or len(self.memory) == 0:
            return
        vectors = np.stack([c.to_vector() for c in self.memory.get_charges()], axis=0)
        d = vectors.shape[1] // 2
        self._faiss_index = FAISSIndex(metric="l2", rerank=True)
        self._faiss_index.add(
            vectors.astype(np.float32),
            z_store=vectors[:, :d],
            sigma_store=np.exp(vectors[:, d:]) + 1e-10,
        )

    @torch.no_grad()
    def update_target_ema(self) -> None:
        self.target_encoder.update_ema()


# -----------------------------------------------------------------------------
# Loss functions
# -----------------------------------------------------------------------------


def nll_loss(
    z_pred: torch.Tensor,
    sigma_pred: torch.Tensor,
    z_target: torch.Tensor,
) -> torch.Tensor:
    """Negative log-likelihood для гауссовского предсказания (диагональная ковариация)."""
    var = sigma_pred**2 + 1e-8
    nll = 0.5 * (torch.log(var) + (z_target - z_pred) ** 2 / var)
    return nll.sum(dim=-1).mean()


def mse_loss(z_pred: torch.Tensor, z_target: torch.Tensor) -> torch.Tensor:
    """MSE в пространстве эмбеддингов (стандартный JEPA)."""
    return ((z_pred - z_target) ** 2).mean()


def jepa_loss(
    z_pred: torch.Tensor,
    sigma_pred: torch.Tensor,
    z_target: torch.Tensor,
    use_nll: bool = True,
) -> torch.Tensor:
    """Комбинированная функция потерь."""
    if use_nll:
        return nll_loss(z_pred, sigma_pred, z_target)
    return mse_loss(z_pred, z_target)
