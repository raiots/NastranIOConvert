from __future__ import annotations

import io
import re
import zipfile
from typing import Tuple

import pandas as pd


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def to_dat_bytes(df: pd.DataFrame) -> bytes:
    out = io.StringIO()
    out.write("node_id Ux Uy Uz\n")
    for row in df.sort_values("node_id").itertuples(index=False):
        out.write(f"{int(row.node_id)} {row.ux:.8e} {row.uy:.8e} {row.uz:.8e}\n")
    return out.getvalue().encode("utf-8")


def to_mode_zip_bytes(scaled_df: pd.DataFrame) -> bytes:
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for mode, group in scaled_df.groupby("mode", sort=False):
            data = group[["node_id", "ux", "uy", "uz"]].to_csv(index=False)
            safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(mode))
            zf.writestr(f"{safe}_deformed.csv", data.encode("utf-8-sig"))
    return bio.getvalue()


def load_text_input(uploaded_file, pasted_text: str) -> Tuple[str, str]:
    if uploaded_file is not None:
        text = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        return text, uploaded_file.name
    return pasted_text, "pasted_text"
