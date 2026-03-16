from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


def build_strain_operator(
    nodes_xyz: pd.DataFrame, edges: pd.DataFrame, component_mode: str = "three_component"
) -> Tuple[np.ndarray, List[Dict[str, float]], List[str], int]:
    node_ids = nodes_xyz["node_id"].to_numpy(int)
    xyz = nodes_xyz.set_index("node_id")[["x", "y", "z"]]
    index = {nid: i for i, nid in enumerate(node_ids.tolist())}
    components, dof_per_node = _component_spec(component_mode)

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
        i = index[int(ni)]
        j = index[int(nj)]
        rows.append(_build_row(i, j, e1, length, len(node_ids), dof_per_node, field="trans"))
        if "torsion" in components:
            rows.append(_build_row(i, j, e1, length, len(node_ids), dof_per_node, field="rot"))
        rows.append(_build_row(i, j, e2, length, len(node_ids), dof_per_node, field="trans"))
        rows.append(_build_row(i, j, e3, length, len(node_ids), dof_per_node, field="trans"))

    if not rows:
        return np.empty((0, len(node_ids) * dof_per_node), dtype=float), meta, components, dof_per_node
    return np.vstack(rows), meta, components, dof_per_node


def solve_displacement_from_strain(B: np.ndarray, strain_vec: np.ndarray, n_nodes: int, dof_per_node: int = 3) -> np.ndarray:
    if B.size == 0:
        return np.zeros(n_nodes * dof_per_node, dtype=float)

    anchor = np.zeros((dof_per_node, n_nodes * dof_per_node), dtype=float)
    for idx in range(dof_per_node):
        anchor[idx, idx] = 1.0

    B_aug = np.vstack([B, anchor])
    y_aug = np.concatenate([strain_vec, np.zeros(dof_per_node, dtype=float)])
    sol, *_ = np.linalg.lstsq(B_aug, y_aug, rcond=None)
    return sol


def build_edge_strain_table(mode: str, meta: List[Dict[str, float]], strain_vec: np.ndarray, components: List[str]) -> pd.DataFrame:
    if not meta:
        cols = ["mode", "node_i", "node_j", "length", "stretch", "torsion", "in_plane_bending", "out_plane_bending", "strain"]
        return pd.DataFrame(columns=cols)

    comp = strain_vec.reshape(-1, len(components))
    rows = []
    for i, info in enumerate(meta):
        values = {name: float(comp[i, idx]) for idx, name in enumerate(components)}
        stretch = float(values.get("stretch", 0.0))
        torsion = float(values.get("torsion", 0.0))
        in_plane = float(values.get("in_plane_bending", 0.0))
        out_plane = float(values.get("out_plane_bending", 0.0))
        eq_src = max(values.items(), key=lambda kv: abs(kv[1])) if values else ("stretch", 0.0)
        equiv = abs(float(eq_src[1]))
        sign = 1.0 if float(eq_src[1]) >= 0 else -1.0
        rows.append(
            {
                "mode": mode,
                "node_i": int(info["node_i"]),
                "node_j": int(info["node_j"]),
                "length": float(info["length"]),
                "stretch": stretch,
                "torsion": torsion,
                "in_plane_bending": in_plane,
                "out_plane_bending": out_plane,
                "strain": sign * equiv,
            }
        )
    return pd.DataFrame(rows)


def _build_row(i: int, j: int, direction: np.ndarray, length: float, n_nodes: int, dof_per_node: int, field: str) -> np.ndarray:
    row = np.zeros(n_nodes * dof_per_node, dtype=float)
    base = 0 if field == "trans" else 3
    row[i * dof_per_node + base : i * dof_per_node + base + 3] = -direction / length
    row[j * dof_per_node + base : j * dof_per_node + base + 3] = direction / length
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


def _component_spec(component_mode: str) -> Tuple[List[str], int]:
    mode = str(component_mode).strip().lower()
    if mode == "four_component":
        return ["stretch", "torsion", "in_plane_bending", "out_plane_bending"], 6
    return ["stretch", "in_plane_bending", "out_plane_bending"], 3
