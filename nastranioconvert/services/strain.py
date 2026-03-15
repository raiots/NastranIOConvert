from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd

from nastranioconvert.models import ModelData
from nastranioconvert.services.reconstruction import build_edge_strain_table, build_strain_operator, solve_displacement_from_strain


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
    mode_weights: Dict[str, float],
    mode_scales: Dict[str, float],
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    grids = model.grids.copy()
    edges = model.edges[["node_i", "node_j"]].copy() if not model.edges.empty else build_fallback_edges(grids)

    summaries = []
    scaled_parts = []
    edge_parts = []

    for mode, group in disp_df.groupby("mode", sort=False):
        joined = _join_mode_displacements(group, grids)
        if joined.empty:
            continue

        B, edge_meta = build_strain_operator(joined[["node_id", "x", "y", "z"]], edges)
        if B.size == 0:
            continue

        u_raw = joined[["ux", "uy", "uz"]].to_numpy(float).reshape(-1)
        eps_raw = B @ u_raw
        scale = float(mode_scales.get(mode, 1.0))
        eps_scaled = eps_raw * scale

        u_scaled = solve_displacement_from_strain(B, eps_scaled, len(joined)).reshape(-1, 3)
        scaled = pd.DataFrame(
            {
                "node_id": joined["node_id"].to_numpy(int),
                "ux": u_scaled[:, 0],
                "uy": u_scaled[:, 1],
                "uz": u_scaled[:, 2],
                "mode": mode,
            }
        )

        edge_mode_df = build_edge_strain_table(mode, edge_meta, eps_raw)
        summaries.append(_build_summary(mode, mode_weights, scale, joined, scaled, edge_mode_df))
        scaled_parts.append(scaled)
        edge_parts.append(edge_mode_df)

    if not summaries:
        raise ValueError("没有可计算的模态数据。请检查 BDF 节点与位移 node_id 是否匹配。")

    summary_df = pd.DataFrame(summaries)
    scaled_df = pd.concat(scaled_parts, ignore_index=True)
    edge_strain_df = pd.concat(edge_parts, ignore_index=True)
    combined_df = _build_weighted_combined(scaled_df, mode_weights)
    return summary_df, scaled_df, edge_strain_df, combined_df


def _join_mode_displacements(group: pd.DataFrame, grids: pd.DataFrame) -> pd.DataFrame:
    xyz_map = grids.set_index("node_id")[["x", "y", "z"]]
    disp = group.groupby("node_id", as_index=False)[["ux", "uy", "uz"]].mean().set_index("node_id")
    return xyz_map.join(disp, how="inner").reset_index()


def _build_summary(
    mode: str,
    mode_weights: Dict[str, float],
    scale: float,
    joined: pd.DataFrame,
    scaled: pd.DataFrame,
    edge_mode_df: pd.DataFrame,
) -> dict:
    raw_norm = np.linalg.norm(joined[["ux", "uy", "uz"]].to_numpy(float), axis=1)
    scaled_norm = np.linalg.norm(scaled[["ux", "uy", "uz"]].to_numpy(float), axis=1)
    return {
        "mode": mode,
        "weight_eta": float(mode_weights.get(mode, 1.0)),
        "input_scale": scale,
        "max_abs_strain_raw": float(edge_mode_df["strain"].abs().max()),
        "max_stretch_raw": float(edge_mode_df["stretch"].abs().max()),
        "max_in_plane_bending_raw": float(edge_mode_df["in_plane_bending"].abs().max()),
        "max_out_plane_bending_raw": float(edge_mode_df["out_plane_bending"].abs().max()),
        "max_disp_raw": float(raw_norm.max()),
        "max_disp_scaled": float(scaled_norm.max()),
        "node_count": int(len(scaled)),
    }


def _build_weighted_combined(scaled_df: pd.DataFrame, mode_weights: Dict[str, float]) -> pd.DataFrame:
    parts = []
    for mode, group in scaled_df.groupby("mode", sort=False):
        eta = float(mode_weights.get(mode, 1.0))
        tmp = group[["node_id", "ux", "uy", "uz"]].copy()
        tmp[["ux", "uy", "uz"]] *= eta
        parts.append(tmp)

    combined = pd.concat(parts, ignore_index=True)
    combined = combined.groupby("node_id", as_index=False)[["ux", "uy", "uz"]].sum()
    combined["disp_mag"] = np.linalg.norm(combined[["ux", "uy", "uz"]].to_numpy(float), axis=1)
    return combined
