from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class ModelData:
    grids: pd.DataFrame
    edges: pd.DataFrame


@dataclass
class ModalData:
    displacements: pd.DataFrame
