from __future__ import annotations

from typing import List


def clean_num(value: str) -> float:
    return float(value.strip().replace("D", "E").replace("d", "e"))


def split_fixed_width(line: str, width: int = 8) -> List[str]:
    raw = line.rstrip("\n")
    return [raw[i : i + width].strip() for i in range(0, len(raw), width)]


def tokenize_bdf_line(line: str) -> List[str]:
    raw = line.rstrip("\n")
    if not raw or raw.lstrip().startswith("$"):
        return []
    if "," in raw:
        return [tok.strip() for tok in raw.split(",")]
    return split_fixed_width(raw)
