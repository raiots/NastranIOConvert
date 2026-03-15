from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def fig_structure_3d(grids: pd.DataFrame, edges: pd.DataFrame | None = None) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter3d(
            x=grids["x"],
            y=grids["y"],
            z=grids["z"],
            mode="markers",
            marker=dict(size=3, color="#1f77b4", opacity=0.8),
            name="nodes",
            customdata=grids["node_id"],
            hovertemplate="node=%{customdata}<br>x=%{x:.3f}<br>y=%{y:.3f}<br>z=%{z:.3f}<extra></extra>",
        )
    )

    if edges is not None and not edges.empty:
        xyz = grids.set_index("node_id")[["x", "y", "z"]]
        xs, ys, zs = [], [], []
        count = 0
        for node_i, node_j in edges[["node_i", "node_j"]].itertuples(index=False):
            if node_i in xyz.index and node_j in xyz.index:
                p1 = xyz.loc[node_i].to_numpy(float)
                p2 = xyz.loc[node_j].to_numpy(float)
                xs.extend([p1[0], p2[0], None])
                ys.extend([p1[1], p2[1], None])
                zs.extend([p1[2], p2[2], None])
                count += 1
            if count > 1800:
                break

        fig.add_trace(
            go.Scatter3d(
                x=xs,
                y=ys,
                z=zs,
                mode="lines",
                line=dict(color="rgba(120,120,120,0.35)", width=2),
                name="edges",
                hoverinfo="skip",
            )
        )

    fig.update_layout(
        title="Structure Preview (Interactive 3D)",
        scene=dict(xaxis_title="X", yaxis_title="Y", zaxis_title="Z", aspectmode="data"),
        margin=dict(l=0, r=0, b=0, t=40),
        height=560,
    )
    return fig


def fig_deformed_overlay_3d(grids: pd.DataFrame, scaled_df: pd.DataFrame, mode: str) -> go.Figure:
    mode_df = scaled_df[scaled_df["mode"] == mode]
    merged = grids.merge(mode_df, on="node_id", how="inner")
    x_def = merged["x"] + merged["ux"]
    y_def = merged["y"] + merged["uy"]
    z_def = merged["z"] + merged["uz"]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter3d(
            x=merged["x"],
            y=merged["y"],
            z=merged["z"],
            mode="markers+lines",
            marker=dict(size=2, color="rgba(100,100,100,0.45)"),
            line=dict(color="rgba(120,120,120,0.45)", width=2),
            name="original",
            customdata=merged["node_id"],
            hovertemplate="node=%{customdata}<br>x=%{x:.3f}<br>y=%{y:.3f}<br>z=%{z:.3f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter3d(
            x=x_def,
            y=y_def,
            z=z_def,
            mode="markers+lines",
            marker=dict(size=5, color="#d62728", opacity=0.95),
            line=dict(color="#d62728", width=4),
            name="scaled",
            customdata=merged["node_id"],
            hovertemplate="node=%{customdata}<br>x=%{x:.3f}<br>y=%{y:.3f}<br>z=%{z:.3f}<extra></extra>",
        )
    )

    x_range = _safe_axis_range(pd.concat([merged["x"], x_def], ignore_index=True))
    y_range = _safe_axis_range(pd.concat([merged["y"], y_def], ignore_index=True))
    z_range = _safe_axis_range(pd.concat([merged["z"], z_def], ignore_index=True))

    fig.update_layout(
        title=f"Mode Overlay (Interactive 3D): {mode}",
        scene=dict(
            xaxis=dict(title="X", range=x_range),
            yaxis=dict(title="Y", range=y_range),
            zaxis=dict(title="Z", range=z_range),
            aspectmode="cube",
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        height=620,
    )
    return fig


def _safe_axis_range(values: pd.Series, min_span: float = 1e-3) -> list[float]:
    lo = float(values.min())
    hi = float(values.max())
    span = hi - lo
    if span < min_span:
        center = 0.5 * (lo + hi)
        half = 0.5 * min_span
        return [center - half, center + half]
    pad = 0.05 * span
    return [lo - pad, hi + pad]


def fig_combined_deformed_3d(grids: pd.DataFrame, combined_df: pd.DataFrame) -> go.Figure:
    merged = grids.merge(combined_df, on="node_id", how="inner")
    fig = px.scatter_3d(
        merged,
        x="x",
        y="y",
        z="z",
        color="disp_mag",
        color_continuous_scale="Turbo",
        opacity=0.9,
        hover_data=["node_id", "ux", "uy", "uz", "disp_mag"],
        title="Combined Displacement Magnitude (Interactive 3D)",
    )
    fig.update_traces(marker=dict(size=3))
    fig.update_layout(
        scene=dict(xaxis_title="X", yaxis_title="Y", zaxis_title="Z", aspectmode="data"),
        margin=dict(l=0, r=0, b=0, t=40),
        height=620,
    )
    return fig
