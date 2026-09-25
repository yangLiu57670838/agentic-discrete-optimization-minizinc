# Derive comparison helpers for cheap vs expensive runs.

from __future__ import annotations

# Kept for import stability; comparison logic lives in schemas.results.
from ado_mzn.schemas.results import compare_runs

__all__ = ["compare_runs"]
