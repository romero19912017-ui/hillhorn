# -*- coding: utf-8 -*-
"""NWF-JEPA: запуск обучения и предсказания с памятью.

Пример: python app.py
"""

from __future__ import annotations

import argparse
from typing import Optional

import numpy as np
import torch

from nwf_jepa import MemoryAwareJEPA, jepa_loss


def train_step(
    model: MemoryAwareJEPA,
    x: torch.Tensor,
    optimizer: torch.optim.Optimizer,
    use_amp: bool = False,
) -> float:
    """Один шаг обучения JEPA (контекст -> таргет)."""
    model.train()
    z_ctx = model.encode_context(x)
    with torch.no_grad():
        z_tgt = model.encode_target(x)
    z_pred, sigma_pred, alpha_pred = model.predict(z_ctx)
    loss = jepa_loss(z_pred, sigma_pred, z_tgt, use_nll=True)
    optimizer.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    optimizer.step()
    model.update_target_ema()
    return loss.detach().item()


def demo_synthetic(
    input_dim: int = 64,
    embed_dim: int = 32,
    batch_size: int = 16,
    steps: int = 200,
) -> None:
    """Демо на синтетических данных."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MemoryAwareJEPA(
        input_dim=input_dim,
        hidden_dim=128,
        embed_dim=embed_dim,
        ema_decay=0.99,
    ).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    for s in range(steps):
        x = torch.randn(batch_size, input_dim, device=device) * 0.5
        loss = train_step(model, x, opt)
        if (s + 1) % 50 == 0:
            print(f"Step {s+1} loss={loss:.4f}")
        if (s + 1) % 20 == 0 and s > 0:
            with torch.no_grad():
                z = model.encode_context(x[:1]).squeeze(0).cpu().numpy()
                sigma = np.ones(embed_dim) * 0.1
                model.add_to_memory(z, sigma, alpha=0.8, label=f"step_{s}")

    model.eval()
    with torch.no_grad():
        x_test = torch.randn(2, input_dim, device=device)
        z_ctx = model.encode_context(x_test)
        similar = model.retrieve_similar(z_ctx[0].cpu().numpy(), k=3)
        z_pred, sigma_pred, alpha_pred = model.predict(z_ctx)
    print("Embedding shape:", z_ctx.shape)
    print("Predicted sigma mean:", sigma_pred.mean().item())
    print("Memory size:", len(model.memory))
    print("Similar retrieved:", len(similar))


def main() -> None:
    parser = argparse.ArgumentParser(description="NWF-JEPA Predictor")
    parser.add_argument("--demo", action="store_true", help="Run synthetic demo")
    parser.add_argument("--steps", type=int, default=200)
    args = parser.parse_args()
    if args.demo or not args.demo:
        demo_synthetic(steps=args.steps)


if __name__ == "__main__":
    main()
