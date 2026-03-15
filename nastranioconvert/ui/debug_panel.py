from __future__ import annotations

import pandas as pd
import streamlit as st


def render_overlay_debug(
    grids: pd.DataFrame,
    scaled_for_overlay: pd.DataFrame,
    mask: pd.Series,
    mode_pick,
    mode_key: str,
) -> None:
    mode_rows = scaled_for_overlay.loc[mask, ["node_id", "ux", "uy", "uz"]].copy()
    merged_rows = grids.merge(mode_rows, on="node_id", how="inner")
    st.write(
        {
            "mode_pick": mode_pick,
            "mode_key": mode_key,
            "scaled_total_rows": int(len(scaled_for_overlay)),
            "mode_rows": int(len(mode_rows)),
            "grid_rows": int(len(grids)),
            "overlay_merged_rows": int(len(merged_rows)),
            "scaled_unique_modes": sorted(scaled_for_overlay["mode"].unique().tolist()),
            "range_info": _build_range_info(mode_rows, merged_rows),
        }
    )
    st.dataframe(mode_rows.head(20), use_container_width=True)


def _build_range_info(mode_rows: pd.DataFrame, merged_rows: pd.DataFrame):
    if merged_rows.empty:
        return {"overlay_ranges": "merged_rows is empty"}

    x0, y0, z0 = merged_rows["x"], merged_rows["y"], merged_rows["z"]
    xd = merged_rows["x"] + merged_rows["ux"]
    yd = merged_rows["y"] + merged_rows["uy"]
    zd = merged_rows["z"] + merged_rows["uz"]
    return {
        "x0_range": [float(x0.min()), float(x0.max())],
        "y0_range": [float(y0.min()), float(y0.max())],
        "z0_range": [float(z0.min()), float(z0.max())],
        "x_def_range": [float(xd.min()), float(xd.max())],
        "y_def_range": [float(yd.min()), float(yd.max())],
        "z_def_range": [float(zd.min()), float(zd.max())],
        "disp_abs_max": {
            "ux": float(mode_rows["ux"].abs().max()),
            "uy": float(mode_rows["uy"].abs().max()),
            "uz": float(mode_rows["uz"].abs().max()),
        },
    }
