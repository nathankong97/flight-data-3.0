"""Helpers for loading airport IATA code lists from the `data/` directory."""

from pathlib import Path
from typing import Iterable, List

from src.config import REPO_ROOT

DATA_DIR = REPO_ROOT / "data"


def load_airport_codes(region: str) -> List[str]:
    """
    Return an ordered list of airport IATA codes for the given region.

    Codes are stored in `data/airport_<REGION>.txt`, one per line. Lines
    beginning with `#` or blank lines are ignored. Results preserve file order
    and duplicate codes are collapsed.
    """
    if not region:
        raise ValueError("region must be a non-empty string")

    file_name = f"airport_{region.upper()}.txt"
    file_path = DATA_DIR / file_name

    if not file_path.exists():
        raise FileNotFoundError(f"Airport list not found: {file_path}")

    seen = set()
    codes: List[str] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        normalized = line.strip().upper()
        if not normalized or normalized.startswith("#"):
            continue
        if normalized not in seen:
            seen.add(normalized)
            codes.append(normalized)
    return codes


def available_regions() -> List[str]:
    """List region tokens inferred from `airport_*.txt` files under `data/`."""
    codes: List[str] = []
    if not DATA_DIR.exists():
        return codes

    for path in DATA_DIR.glob("airport_*.txt"):
        suffix = path.stem.replace("airport_", "")
        if suffix:
            codes.append(suffix.upper())
    return sorted(set(codes))


__all__ = ["load_airport_codes", "available_regions"]
