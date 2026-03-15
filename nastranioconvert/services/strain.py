from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd

from nastranioconvert.models import ModelData


def build_fallback_edges(grids: pd.DataFrame, k: int = 2) -> pd.DataFrame:
    xyz = grids[["x", "y", "z"]].to_numpy(float)
    node_ids = grids["node_id"].to_numpy(int)
    edges = set()
    for idx in range(len(node_ids)):
        dist = np.linalg.norm(xyz - xyz[idx], axis=1)
        order = np.argsort(dist)
        for j in order[1 : 1 + k]:
            a, b = sorted((int(node_ids[idx]), int(node_ids[j])))
            edges.add((a, b))
    return pd.DataFrame(sorted(edges), columns=["node_i", "node_j"])


def estimate_mode_strain(
    model: ModelData,
    disp_df: pd.DataFrame,
    epsilon_allow: float,
    mode_weights: Dict[str, float],
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    grids = model.grids.copy()
    edge_df = model.edges[["node_i", "node_j"]].copy() if not model.edges.empty else build_fallback_edges(grids)
    xyz_map = grids.set_index("node_id")[["x", "y", "z"]]

    summaries = []
    scaled_parts = []
    edge_strain_parts = []

    for mode, group in disp_df.groupby("mode", sort=False):
        joined = _join_mode_displacements(group, xyz_map)
        if joined.empty:
            continue

        edge_mode_df = _compute_mode_edge_strain(edge_df, xyz_map, joined, mode)
        if edge_mode_df.empty:
            continue

        scaled_df, summary = _build_scaled_mode_result(joined, edge_mode_df, mode, epsilon_allow, mode_weights)
        summaries.append(summary)
        scaled_parts.append(scaled_df)
        edge_strain_parts.append(edge_mode_df)

    if not summaries:
        raise ValueError("没有可计算的模态数据。请检查 BDF 节点与位移 node_id 是否匹配。")

    summary_df = pd.DataFrame(summaries)
    scaled_df = pd.concat(scaled_parts, ignore_index=True)
    edge_strain_df = pd.concat(edge_strain_parts, ignore_index=True)
    combined_df = _build_weighted_combined(scaled_df, mode_weights)
    return summary_df, scaled_df, edge_strain_df, combined_df


def _join_mode_displacements(group: pd.DataFrame, xyz_map: pd.DataFrame) -> pd.DataFrame:
    mode_mean = group.groupby("node_id", as_index=False)[["ux", "uy", "uz"]].mean().set_index("node_id")
    return xyz_map.join(mode_mean, how="inner").reset_index()


def _compute_mode_edge_strain(edge_df: pd.DataFrame, xyz_map: pd.DataFrame, joined: pd.DataFrame, mode: str) -> pd.DataFrame:
    dmap = joined.set_index("node_id")[["ux", "uy", "uz"]]
    rows = []
    for node_i, node_j in edge_df[["node_i", "node_j"]].itertuples(index=False):
        if node_i not in xyz_map.index or node_j not in xyz_map.index:
            continue
        if node_i not in dmap.index or node_j not in dmap.index:
            continue

        xi = xyz_map.loc[node_i].to_numpy(float)
        xj = xyz_map.loc[node_j].to_numpy(float)
        length = np.linalg.norm(xj - xi)
        if length <= 1e-12:
            continue

        direction = (xj - xi) / length
        ui = np.asarray(dmap.loc[node_i], dtype=float).reshape(-1)
        uj = np.asarray(dmap.loc[node_j], dtype=float).reshape(-1)
        if ui.size != 3 or uj.size != 3:
            continue

        strain = float(np.dot(uj - ui, direction) / length)
        rows.append((mode, int(node_i), int(node_j), length, strain))

    return pd.DataFrame(rows, columns=["mode", "node_i", "node_j", "length", "strain"])


def _build_scaled_mode_result(
    joined: pd.DataFrame,
    edge_mode_df: pd.DataFrame,
    mode: str,
    epsilon_allow: float,
    mode_weights: Dict[str, float],
) -> Tuple[pd.DataFrame, dict]:
    max_abs_strain = float(edge_mode_df["strain"].abs().max())
    scale = epsilon_allow / max_abs_strain if max_abs_strain > 0 else 1.0

    scaled = joined[["node_id", "ux", "uy", "uz"]].copy()
    scaled[["ux", "uy", "uz"]] *= scale
    scaled["mode"] = mode

    raw_norm = np.linalg.norm(joined[["ux", "uy", "uz"]].to_numpy(float), axis=1)
    scaled_norm = np.linalg.norm(scaled[["ux", "uy", "uz"]].to_numpy(float), axis=1)

    summary = {
        "mode": mode,
        "weight_eta": mode_weights.get(mode, 1.0),
        "max_abs_strain_raw": max_abs_strain,
        "epsilon_allow": epsilon_allow,
        "suggested_scale": scale,
        "max_disp_raw": float(raw_norm.max()),
        "max_disp_scaled": float(scaled_norm.max()),
        "node_count": int(len(scaled)),
    }
    return scaled, summary


def _build_weighted_combined(scaled_df: pd.DataFrame, mode_weights: Dict[str, float]) -> pd.DataFrame:
    parts = []
    for mode, group in scaled_df.groupby("mode", sort=False):
        eta = mode_weights.get(mode, 1.0)
        tmp = group[["node_id", "ux", "uy", "uz"]].copy()
        tmp[["ux", "uy", "uz"]] *= eta
        parts.append(tmp)

    combined = pd.concat(parts, ignore_index=True)
    combined = combined.groupby("node_id", as_index=False)[["ux", "uy", "uz"]].sum()
    combined["disp_mag"] = np.linalg.norm(combined[["ux", "uy", "uz"]].to_numpy(float), axis=1)
    return combined
