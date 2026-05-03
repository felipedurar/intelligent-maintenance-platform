from __future__ import annotations

from dataclasses import dataclass
from typing import Self

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from torch import nn


class MaintenanceMLP(nn.Module):
    def __init__(self, input_dim: int, hidden_dims: tuple[int, ...], dropout: float) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        previous_dim = input_dim
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(previous_dim, hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            previous_dim = hidden_dim
        layers.append(nn.Linear(previous_dim, 1))
        self.network = nn.Sequential(*layers)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.network(inputs).squeeze(-1)


@dataclass
class TorchMLPClassifier:
    """Small sklearn-like PyTorch MLP classifier for AI4I tabular features."""

    hidden_dims: tuple[int, ...] = (32, 16)
    dropout: float = 0.2
    learning_rate: float = 0.001
    epochs: int = 60
    patience: int = 8
    random_state: int = 42
    threshold: float = 0.5

    def __post_init__(self) -> None:
        self.scaler = StandardScaler()
        self.model: MaintenanceMLP | None = None

    def fit(self, x: pd.DataFrame, y: pd.Series) -> Self:
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)

        x_scaled = self.scaler.fit_transform(x).astype(np.float32)
        y_array = y.astype(int).to_numpy(dtype=np.float32)
        x_tensor = torch.tensor(x_scaled, dtype=torch.float32)
        y_tensor = torch.tensor(y_array, dtype=torch.float32)

        self.model = MaintenanceMLP(
            input_dim=x.shape[1],
            hidden_dims=self.hidden_dims,
            dropout=self.dropout,
        )
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)

        positive_count = float(y_array.sum())
        negative_count = float(len(y_array) - positive_count)
        pos_weight = negative_count / positive_count if positive_count > 0 else 1.0
        criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(pos_weight, dtype=torch.float32))

        best_loss = float("inf")
        best_state = None
        epochs_without_improvement = 0
        for _ in range(self.epochs):
            self.model.train()
            optimizer.zero_grad()
            logits = self.model(x_tensor)
            loss = criterion(logits, y_tensor)
            loss.backward()
            optimizer.step()

            current_loss = float(loss.detach().item())
            if current_loss + 1e-6 < best_loss:
                best_loss = current_loss
                best_state = {
                    key: value.detach().clone()
                    for key, value in self.model.state_dict().items()
                }
                epochs_without_improvement = 0
            else:
                epochs_without_improvement += 1
            if epochs_without_improvement >= self.patience:
                break

        if best_state is not None:
            self.model.load_state_dict(best_state)
        return self

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("TorchMLPClassifier must be fitted before prediction.")
        x_scaled = self.scaler.transform(x).astype(np.float32)
        x_tensor = torch.tensor(x_scaled, dtype=torch.float32)
        self.model.eval()
        with torch.no_grad():
            probabilities = torch.sigmoid(self.model(x_tensor)).numpy()
        return np.column_stack([1.0 - probabilities, probabilities])

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        probabilities = self.predict_proba(x)[:, 1]
        return (probabilities >= self.threshold).astype(int)

    def get_params(self, deep: bool = True) -> dict[str, object]:
        return {
            "hidden_dims": self.hidden_dims,
            "dropout": self.dropout,
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "patience": self.patience,
            "random_state": self.random_state,
            "threshold": self.threshold,
        }

    def set_params(self, **params: object) -> Self:
        for key, value in params.items():
            setattr(self, key, value)
        return self
