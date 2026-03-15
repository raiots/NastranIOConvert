from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from nastranioconvert.parsers import parse_bdf_text, parse_modal_text, parse_mode_weights
from nastranioconvert.services import estimate_mode_strain
from nastranioconvert.utils.io import load_text_input, to_csv_bytes, to_dat_bytes, to_mode_zip_bytes
from nastranioconvert.visualization import fig_combined_deformed_3d, fig_deformed_overlay_3d, fig_structure_3d

GITHUB_REPO_URL = "https://github.com/raiots/NastranIOConvert"


def main() -> None:
    st.set_page_config(page_title="Nastran 模态变形转换工具", layout="wide")
    _render_brand_header()
    st.title("Nastran 模态变形转换工具")
    st.caption("流程：BDF/结果导入 -> 位移转应变(边轴向估计) -> 应变约束放大 -> 可视化与导出")

    bdf_text, modal_text, modal_name, epsilon_allow, eta_raw = _render_inputs()
    if not bdf_text.strip() or not modal_text.strip():
        st.info("请提供 BDF 和模态位移数据（上传或粘贴均可）。")
        st.stop()

    with st.spinner("正在解析输入并自动处理..."):
        model = parse_bdf_text(bdf_text)
        modal = parse_modal_text(modal_text, modal_name)
        mode_order = list(pd.unique(modal.displacements["mode"]))
        mode_weights = parse_mode_weights(eta_raw, mode_order)
        summary_df, scaled_df, edge_strain_df, combined_df = estimate_mode_strain(
            model,
            modal.displacements,
            epsilon_allow,
            mode_weights,
        )

    st.success("自动处理完成。")
    _render_results(model, summary_df, scaled_df, edge_strain_df, combined_df)


def _render_brand_header() -> None:
    left, right = st.columns([5, 1])
    with left:
        st.markdown("#### MAAL | Manufacturing and Aerospace Automation Lab")
    with right:
        icon = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" '
            'viewBox="0 0 16 16" fill="#111">'
            '<path d="M8 0C3.58 0 0 3.58 0 8a8 8 0 0 0 5.47 7.59c.4.07.55-.17.55-.38'
            ' 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13'
            '-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66'
            ' .07-.52.28-.87.5-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15'
            '-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27'
            ' .68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12'
            ' .51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48'
            ' 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42'
            '-3.58-8-8-8z"/></svg>'
        )
        st.markdown(f'<a href="{GITHUB_REPO_URL}" target="_blank">{icon}</a>', unsafe_allow_html=True)


def _render_inputs():
    st.markdown("### 1) 输入")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("结构模型(BDF)")
        bdf_upload = st.file_uploader("上传 BDF 文件", type=["bdf", "dat", "txt"], key="bdf_uploader")
        bdf_paste = st.text_area("或粘贴 BDF 文本", height=220, value="", placeholder="粘贴 GRID/CBAR 等卡片...")

    with col2:
        st.subheader("模态位移")
        modal_upload = st.file_uploader("上传位移文件 (CSV/F06/TXT)", type=["csv", "f06", "txt"], key="modal_uploader")
        modal_paste = st.text_area(
            "或粘贴位移文本",
            height=220,
            value="",
            placeholder="CSV: node_id,ux,uy,uz[,mode] 或 F06 位移表文本",
        )

    st.markdown("### 2) 参数")
    p1, p2 = st.columns([1, 2])
    with p1:
        epsilon_allow = st.number_input("允许最大应变 epsilon_allow", min_value=1e-8, value=0.002, step=0.0001, format="%.6f")
    with p2:
        eta_raw = st.text_input("模态权重 eta (可选)", value="", help="例: 1.0,0.8 或 Mode1=1.0,Mode2=0.6")

    bdf_text, _ = load_text_input(bdf_upload, bdf_paste)
    modal_text, modal_name = load_text_input(modal_upload, modal_paste)
    return bdf_text, modal_text, modal_name, epsilon_allow, eta_raw


def _render_results(model, summary_df, scaled_df, edge_strain_df, combined_df) -> None:
    st.markdown("### 3) 过程可视化")
    k1, k2, k3 = st.columns(3)
    k1.metric("BDF节点数", f"{len(model.grids):,}")
    k2.metric("结构边数(CBAR/自动补边)", f"{len(model.edges) if not model.edges.empty else 'fallback'}")
    k3.metric("模态数", f"{summary_df['mode'].nunique()}")

    st.dataframe(summary_df, use_container_width=True)

    v1, v2 = st.columns(2)
    with v1:
        edges = model.edges if not model.edges.empty else None
        st.plotly_chart(fig_structure_3d(model.grids, edges), use_container_width=True)
    with v2:
        hist_fig = px.histogram(edge_strain_df, x="strain", nbins=50, title="Edge Strain Distribution (Raw)")
        hist_fig.update_layout(height=560, margin=dict(l=10, r=10, b=10, t=40))
        st.plotly_chart(hist_fig, use_container_width=True)

    modes = summary_df["mode"].tolist()
    mode_pick = st.selectbox("查看某个模态的变形叠加图", options=modes, index=0)
    v3, v4 = st.columns(2)
    with v3:
        st.plotly_chart(fig_deformed_overlay_3d(model.grids, scaled_df, mode_pick), use_container_width=True)
    with v4:
        st.plotly_chart(fig_combined_deformed_3d(model.grids, combined_df), use_container_width=True)

    st.markdown("### 4) 结果输出")
    st.subheader("加权组合后的位移场")
    st.dataframe(combined_df.sort_values("node_id"), use_container_width=True)

    st.download_button("下载 summary.csv", to_csv_bytes(summary_df), "summary.csv", "text/csv")
    st.download_button("下载 combined_deformed.csv", to_csv_bytes(combined_df.sort_values("node_id")), "combined_deformed.csv", "text/csv")
    st.download_button("下载 combined_deformed.dat", to_dat_bytes(combined_df[["node_id", "ux", "uy", "uz"]]), "combined_deformed.dat", "text/plain")
    st.download_button("下载各模态结果 ZIP", to_mode_zip_bytes(scaled_df), "mode_deformed_outputs.zip", "application/zip")

    st.caption("说明：应变计算采用基于结构边方向的轴向应变估算，用于快速调试与倍率建议。")
