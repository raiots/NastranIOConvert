from __future__ import annotations

import io
import re
from typing import Dict, Iterable

import pandas as pd

from nastranioconvert.models import ModalData
from nastranioconvert.utils.text import clean_num


def parse_displacement_csv_text(text: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(text))
    cols = {col.lower().strip(): col for col in df.columns}

    node_col = cols.get("node_id") or cols.get("nid") or cols.get("grid") or cols.get("id")
    ux_col = cols.get("ux") or cols.get("t1") or cols.get("u")
    uy_col = cols.get("uy") or cols.get("t2") or cols.get("v")
    uz_col = cols.get("uz") or cols.get("t3") or cols.get("w")
    r1_col = cols.get("r1") or cols.get("rx") or cols.get("rotx") or cols.get("theta_x") or cols.get("rot_x")
    r2_col = cols.get("r2") or cols.get("ry") or cols.get("roty") or cols.get("theta_y") or cols.get("rot_y")
    r3_col = cols.get("r3") or cols.get("rz") or cols.get("rotz") or cols.get("theta_z") or cols.get("rot_z")
    mode_col = cols.get("mode") or cols.get("mode_id") or cols.get("imode")

    if not all([node_col, ux_col, uy_col, uz_col]):
        raise ValueError("位移 CSV 需要包含 node_id(同义列) 与 ux/uy/uz(或 t1/t2/t3)。")

    out = pd.DataFrame(
        {
            "node_id": pd.to_numeric(df[node_col], errors="coerce").astype("Int64"),
            "ux": pd.to_numeric(df[ux_col], errors="coerce"),
            "uy": pd.to_numeric(df[uy_col], errors="coerce"),
            "uz": pd.to_numeric(df[uz_col], errors="coerce"),
            "r1": pd.to_numeric(df[r1_col], errors="coerce") if r1_col else 0.0,
            "r2": pd.to_numeric(df[r2_col], errors="coerce") if r2_col else 0.0,
            "r3": pd.to_numeric(df[r3_col], errors="coerce") if r3_col else 0.0,
        }
    )
    out["mode"] = df[mode_col].astype(str) if mode_col else "Mode1"
    out = out.dropna(subset=["node_id", "ux", "uy", "uz"]).copy()
    out["node_id"] = out["node_id"].astype(int)

    if out.empty:
        raise ValueError("位移 CSV 解析后为空，请检查列名和内容。")
    return out


def parse_f06_displacements(text: str) -> pd.DataFrame:
    rows = []
    mode = "Mode1"
    in_disp_block = False
    mode_idx = 1

    mode_pat = re.compile(r"^\s*EIGENVALUE\s*=\s*([\dE+\-.]+)", re.IGNORECASE)
    disp_pat = re.compile(
        r"^\s*(\d+)\s+G\s+([-+]?\d*\.?\d+(?:[EDed][-+]?\d+)?)\s+"
        r"([-+]?\d*\.?\d+(?:[EDed][-+]?\d+)?)\s+([-+]?\d*\.?\d+(?:[EDed][-+]?\d+)?)\s+"
        r"([-+]?\d*\.?\d+(?:[EDed][-+]?\d+)?)\s+([-+]?\d*\.?\d+(?:[EDed][-+]?\d+)?)\s+"
        r"([-+]?\d*\.?\d+(?:[EDed][-+]?\d+)?)"
    )

    block_markers = [
        "D I S P L A C E M E N T   V E C T O R",
        "R E A L   E I G E N V E C T O R",
    ]

    for line in text.splitlines():
        if mode_pat.search(line):
            mode = f"Mode{mode_idx}"
            mode_idx += 1
            continue

        if any(marker in line for marker in block_markers):
            in_disp_block = True
            continue

        if in_disp_block and _is_f06_block_end(line):
            in_disp_block = False
            continue

        if in_disp_block:
            match = disp_pat.match(line)
            if match:
                rows.append(
                    (
                        mode,
                        int(match.group(1)),
                        clean_num(match.group(2)),
                        clean_num(match.group(3)),
                        clean_num(match.group(4)),
                        clean_num(match.group(5)),
                        clean_num(match.group(6)),
                        clean_num(match.group(7)),
                    )
                )

    if not rows:
        raise ValueError("未从 F06 中识别到 G 点位移表，可改用 CSV(node_id,ux,uy,uz)。")

    return pd.DataFrame(rows, columns=["mode", "node_id", "ux", "uy", "uz", "r1", "r2", "r3"])


def parse_modal_text(text: str, filename_hint: str = "") -> ModalData:
    hint = filename_hint.lower()
    stripped = text.lstrip()
    first_line = stripped.splitlines()[0] if stripped else ""
    try_csv_first = "," in first_line

    if hint.endswith(".csv") or try_csv_first:
        disp = parse_displacement_csv_text(text)
    elif hint.endswith(".f06"):
        disp = parse_f06_displacements(text)
    else:
        try:
            disp = parse_displacement_csv_text(text)
        except Exception:
            disp = parse_f06_displacements(text)

    return ModalData(displacements=disp)


def parse_mode_weights(raw: str, modes: Iterable[str]) -> Dict[str, float]:
    return parse_mode_values(raw, modes, default=1.0)


def parse_mode_scales(raw: str, modes: Iterable[str]) -> Dict[str, float]:
    return parse_mode_values(raw, modes, default=1.0)


def parse_mode_values(raw: str, modes: Iterable[str], default: float = 1.0) -> Dict[str, float]:
    mode_list = list(modes)
    result = {mode: default for mode in mode_list}
    raw = raw.strip()
    if not raw:
        return result

    if "," not in raw and "=" not in raw and ":" not in raw:
        value = float(raw)
        return {mode: value for mode in mode_list}

    if "=" not in raw and ":" not in raw:
        vals = [v.strip() for v in raw.split(",") if v.strip()]
        for idx, value in enumerate(vals[: len(mode_list)]):
            result[mode_list[idx]] = float(value)
        return result

    for item in [v.strip() for v in raw.split(",") if v.strip()]:
        sep = "=" if "=" in item else ":"
        key, value = item.split(sep, 1)
        result[key.strip()] = float(value.strip())
    return result


def _is_f06_block_end(line: str) -> bool:
    end_markers = [
        "F O R C E S   O F   S I N G L E - P O I N T   C O N S T R A I N T",
        "S T R E S S E S",
        "S T R A I N",
    ]
    return any(marker in line for marker in end_markers)
