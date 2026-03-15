from __future__ import annotations

import re
from typing import List, Tuple

import pandas as pd

from nastranioconvert.models import ModelData
from nastranioconvert.utils.text import clean_num, tokenize_bdf_line


def parse_bdf_text(text: str) -> ModelData:
    grids: List[Tuple[int, float, float, float]] = []
    edges: List[Tuple[int, int, int]] = []
    lines = text.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        fields = tokenize_bdf_line(line)
        if not fields:
            i += 1
            continue

        card = fields[0].upper().replace("*", "")
        if card == "GRID":
            raw = line.rstrip("\n")
            if fields[0].upper().startswith("GRID*") and i + 1 < len(lines):
                next_line = lines[i + 1].rstrip("\n")
                if next_line.lstrip().startswith("*"):
                    raw = f"{raw} {next_line}"
                    i += 1

            nums = re.findall(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[EDed][-+]?\d+)?", raw)
            if len(nums) >= 4:
                _parse_grid_line(nums, grids)

        elif card == "CBAR" and len(fields) >= 5:
            _parse_cbar_line(fields, edges)

        i += 1

    grid_df = pd.DataFrame(grids, columns=["node_id", "x", "y", "z"])
    grid_df = grid_df.drop_duplicates("node_id")
    edge_df = pd.DataFrame(edges, columns=["elem_id", "node_i", "node_j"])
    edge_df = edge_df.drop_duplicates("elem_id")

    if grid_df.empty:
        raise ValueError("BDF 中没有成功解析到 GRID 节点。")

    return ModelData(grids=grid_df, edges=edge_df)


def _parse_grid_line(nums: List[str], grids: List[Tuple[int, float, float, float]]) -> None:
    try:
        gid = int(float(nums[0]))
        rest = nums[1:]
        if len(rest) >= 4 and re.fullmatch(r"[-+]?\d+", rest[0] or ""):
            xyz = rest[1:4]
        else:
            xyz = rest[:3]
        if len(xyz) < 3:
            return
        grids.append((gid, clean_num(xyz[0]), clean_num(xyz[1]), clean_num(xyz[2])))
    except ValueError:
        return


def _parse_cbar_line(fields: List[str], edges: List[Tuple[int, int, int]]) -> None:
    try:
        elem_id = int(fields[1])
        node_i = int(fields[3])
        node_j = int(fields[4])
        edges.append((elem_id, node_i, node_j))
    except ValueError:
        return
