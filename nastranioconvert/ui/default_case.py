from __future__ import annotations

from pathlib import Path
from typing import Tuple

import streamlit as st


@st.cache_data(show_spinner=False)
def get_default_case_texts() -> Tuple[str, str]:
    root = Path(__file__).resolve().parents[2]
    bdf_path = root / "data" / "tbeamf.bdf"
    f06_path = root / "data" / "tbeamf.f06"
    bdf_text = bdf_path.read_text(encoding="utf-8", errors="ignore") if bdf_path.exists() else ""
    f06_text = f06_path.read_text(encoding="utf-8", errors="ignore") if f06_path.exists() else ""
    return bdf_text, f06_text
