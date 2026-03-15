from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


def build_strain_operator(nodes_xyz: pd.DataFrame, edges: pd.DataFrame) -> Tuple[np.ndarray, List[Dict[str, float]]]:
    node_ids = nodes_xyz["node_id"].to_numpy(int)
    xyz = nodes_xyz.set_index("node_id")[["x", "y", "z"]]
    index = {nid: i for i, nid in enumerate(node_ids.tolist())}

    rows: List[np.ndarray] = []
    meta: List[Dict[str, float]] = []
    for ni, nj in edges[["node_i", "node_j"]].itertuples(index=False):
        if ni not in index or nj not in index:
            continue

        xi = xyz.loc[ni].to_numpy(float)
        xj = xyz.loc[nj].to_numpy(float)
        length = float(np.linalg.norm(xj - xi))
        if length <= 1e-12:
            continue

        e1, e2, e3 = _build_local_frame(xj - xi)
        meta.append({"node_i": int(ni), "node_j": int(nj), "length": length})
        rows.extend(
            [
                _build_row(index[int(ni)], index[int(nj)], e1, length, len(node_ids)),
                _build_row(index[int(ni)], index[int(nj)], e2, length, len(node_ids)),
                _build_row(index[int(ni)], index[int(nj)], e3, length, len(node_ids)),
            ]
        )

    if not rows:
        return np.empty((0, len(node_ids) * 3), dtype=float), meta
    return np.vstack(rows), meta


def solve_displacement_from_strain(B: np.ndarray, strain_vec: np.ndarray, n_nodes: int) -> np.ndarray:
    if B.size == 0:
        return np.zeros(n_nodes * 3, dtype=float)

    anchor = np.zeros((3, n_nodes * 3), dtype=float)
    anchor[0, 0] = 1.0
    anchor[1, 1] = 1.0
    anchor[2, 2] = 1.0

    B_aug = np.vstack([B, anchor])
    y_aug = np.concatenate([strain_vec, np.zeros(3, dtype=float)])
    sol, *_ = np.linalg.lstsq(B_aug, y_aug, rcond=None)
    return sol


def build_edge_strain_table(mode: str, meta: List[Dict[str, float]], strain_vec: np.ndarray) -> pd.DataFrame:
    if not meta:
        cols = ["mode", "node_i", "node_j", "length", "stretch", "in_plane_bending", "out_plane_bending", "strain"]
        return pd.DataFrame(columns=cols)

    comp = strain_vec.reshape(-1, 3)
    rows = []
    for i, info in enumerate(meta):
        stretch = float(comp[i, 0])
        in_plane = float(comp[i, 1])
        out_plane = float(comp[i, 2])
        equiv = max(abs(stretch), abs(in_plane), abs(out_plane))
        rows.append(
            {
                "mode": mode,
                "node_i": int(info["node_i"]),
                "node_j": int(info["node_j"]),
                "length": float(info["length"]),
                "stretch": stretch,
                "in_plane_bending": in_plane,
                "out_plane_bending": out_plane,
                "strain": equiv if stretch >= 0 else -equiv,
            }
        )
    return pd.DataFrame(rows)


def _build_row(i: int, j: int, direction: np.ndarray, length: float, n_nodes: int) -> np.ndarray:
    row = np.zeros(n_nodes * 3, dtype=float)
    row[i * 3 : i * 3 + 3] = -direction / length
    row[j * 3 : j * 3 + 3] = direction / length
    return row


def _build_local_frame(axis_vec: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    e1 = _normalize(axis_vec)
    ref = np.array([0.0, 0.0, 1.0]) if abs(float(np.dot(e1, [0.0, 0.0, 1.0]))) < 0.9 else np.array([0.0, 1.0, 0.0])
    e2 = _normalize(np.cross(ref, e1))
    e3 = _normalize(np.cross(e1, e2))
    return e1, e2, e3


def _normalize(v: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(v))
    if norm <= 1e-12:
        return np.array([1.0, 0.0, 0.0])
    return v / norm
