import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "alphaforge-brain" / "src"))

from domain.data.ingest_nvda import (  # noqa: E402
    load_canonical_dataset,
    slice_canonical,
)

canonical, _ = load_canonical_dataset()
start = 1609459200000
end = 1640995200000

ts_values = pd.to_numeric(canonical["ts"], errors="coerce").to_numpy(
    dtype="float64", copy=False
)
mask = np.ones_like(ts_values, dtype=bool)
start_mask = ts_values >= float(start)
start_mask[np.isnan(ts_values)] = False
mask &= start_mask
end_mask = ts_values <= float(end)
end_mask[np.isnan(ts_values)] = False
mask &= end_mask

print("mask dtype", mask.dtype, "len", len(mask), "true count", mask.sum())
print("any non bool", any(type(x) is not np.bool_ for x in mask))
selected = np.flatnonzero(mask)
print("indices dtype", selected.dtype, "len", len(selected))
print("first entries", selected[:5])
print("slice len via iloc", len(canonical.iloc[selected]))
print("slice len via func", len(slice_canonical(start, end)))
