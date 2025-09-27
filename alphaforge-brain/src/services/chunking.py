from __future__ import annotations

import inspect
import re
from collections.abc import Iterable, Iterator
from typing import Callable

import pandas as pd


def iter_chunk_slices(
    n_rows: int, chunk_size: int, overlap: int = 0
) -> Iterator[tuple[int, int, int]]:
    """Yield deterministic chunk slice tuples for DataFrame .iloc slicing.

    Yields tuples of (read_start, read_end, drop_prefix) where:
    - read_start/read_end are 0-based half-open indices for the input array.
    - drop_prefix indicates how many leading rows to drop from the computed result
      for this chunk to avoid duplication from the overlap region. This equals the
      number of rows that belong to prior chunks within the read window, i.e.,
      drop_prefix = chunk_start - read_start.

    Rules:
    - Chunks are emitted in ascending order and preserve index ordering.
    - The first chunk never uses a negative start and has drop_prefix=0.
    - For subsequent chunks, `read_start` includes the overlap from the prior chunk,
      and `drop_prefix` equals the number of overlapped rows preceding the new
      chunk's unique region: drop_prefix = i - read_start.
    - The last chunk is not extended beyond n_rows; only prior-overlap is used.

    Edge cases:
    - If chunk_size <= 0, treat as single monolithic chunk (0, n_rows, 0).
    - If n_rows == 0, yields nothing.
    - If overlap < 0, it's clamped to 0.
    """
    if n_rows <= 0:
        return
    if chunk_size <= 0 or chunk_size >= n_rows:
        yield (0, n_rows, 0)
        return
    ov = max(0, int(overlap))
    i = 0
    while i < n_rows:
        start = 0 if i == 0 else max(0, i - ov)
        end = min(n_rows, i + chunk_size)
        drop = 0 if i == 0 else i - start
        # drop must never exceed the size of the window
        if drop > (end - start):
            drop = max(0, end - start)
        yield (start, end, drop)
        if end >= n_rows:
            break
        i = end


def compute_required_overlap(indicators: Iterable[object]) -> int:
    """Compute overlap policy: max(required_window_sizes) - 1.

    Heuristics:
    - If an indicator exposes integer attribute `window`, use it.
    - If it exposes a sequence `windows`, use max of ints within.
    - If it exposes numeric attributes `short_window`/`long_window`, use their max.
    - Otherwise, ignore that indicator (treated as no explicit rolling window).
    Returns 0 if no window info found.
    """
    max_w = 0
    for ind in indicators:
        w = 0
        if hasattr(ind, "window") and isinstance(ind.window, int):
            w = int(ind.window)
        elif hasattr(ind, "windows"):
            win = ind.windows
            try:
                vals = [int(x) for x in win if isinstance(x, (int,))]
                w = max(vals) if vals else 0
            except Exception:
                w = 0
        else:
            sw = getattr(ind, "short_window", None)
            lw = getattr(ind, "long_window", None)
            cand = [int(x) for x in (sw, lw) if isinstance(x, int)]
            w = max(cand) if cand else 0
            # Fallback for function-style indicators: introspect defaults
            if w == 0 and callable(ind):
                try:
                    sig = inspect.signature(ind)
                    defaults = {
                        k: v.default
                        for k, v in sig.parameters.items()
                        if v.default is not inspect._empty
                    }
                    # Look for common names
                    cands: list[int] = []
                    for key in ("window", "short_window", "long_window"):
                        val = defaults.get(key)
                        if isinstance(val, int):
                            cands.append(val)
                    # If there's a sequence default under 'windows'
                    valw = defaults.get("windows")
                    if isinstance(valw, (list, tuple)):
                        for x in valw:
                            if isinstance(x, int):
                                cands.append(int(x))
                    if cands:
                        w = max(cands)
                except Exception:
                    pass
        if w > max_w:
            max_w = w
    return max(0, max_w - 1)


__all__ = ["iter_chunk_slices", "compute_required_overlap"]


def compute_required_overlap_for_functions(
    functions: dict[str, Callable[[pd.DataFrame], pd.DataFrame | pd.Series]],
    df_sample: pd.DataFrame,
    base_columns: Iterable[str],
) -> int:
    """Infer overlap from function-style indicators by inspecting output column names.

    We apply each function to a small sample DataFrame and parse integers present in
    non-base column names (e.g., "sma_long_50" -> 50). The required overlap is the
    maximum such inferred window minus 1.

    This is a heuristic used only when explicit indicator window metadata is not available.
    """
    base: set[str] = set(map(str, base_columns))
    max_w = 0
    for _name, fn in functions.items():
        try:
            out = fn(df_sample)
        except Exception:
            continue
        if isinstance(out, pd.Series):
            cols = [out.name] if out.name is not None else []
        elif isinstance(out, pd.DataFrame):
            cols = list(map(str, out.columns))
        elif (
            isinstance(out, (list, tuple))
            and out
            and isinstance(out[0], (pd.DataFrame, pd.Series))
        ):
            o = out[0]
            if isinstance(o, pd.Series):
                cols = [o.name] if o.name is not None else []
            else:
                cols = list(map(str, o.columns))
        else:
            continue
        for c in cols:
            if c in base:
                continue
            nums = [int(x) for x in re.findall(r"(\d+)", c)]
            if nums:
                max_w = max(max_w, max(nums))
    return max(0, max_w - 1)


__all__.append("compute_required_overlap_for_functions")


# ---- Adaptive chunk sizing helpers (T007/T008) ----


def estimate_row_size_bytes_from_df(df: pd.DataFrame) -> int:
    """Estimate average bytes per row based on dtypes.

    Heuristics for common pandas dtypes; object columns are approximated.
    """
    total = 0
    for dtype in df.dtypes:
        if pd.api.types.is_integer_dtype(dtype) or pd.api.types.is_float_dtype(dtype):
            total += int(dtype.itemsize)
        elif pd.api.types.is_bool_dtype(dtype):
            total += 1
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            total += 8
        elif pd.api.types.is_categorical_dtype(dtype):
            # pointer + category code ~ 8 bytes
            total += 8
        else:
            # object/string: rough average payload
            total += 64
    return max(1, total)


def choose_chunk_size(
    df: pd.DataFrame,
    *,
    target_chunk_mb: int = 256,
    max_rows_cap: int = 2_000_000,
) -> int:
    """Choose a chunk size in rows given a target memory per chunk.

    - Uses dtype-based row size estimate
    - Caps at max_rows_cap
    - Returns at least 1
    """
    row_bytes = estimate_row_size_bytes_from_df(df)
    budget_bytes = max(1, int(target_chunk_mb) * 1024 * 1024)
    rows = max(1, min(int(budget_bytes // row_bytes), int(max_rows_cap)))
    return rows


__all__.extend(["estimate_row_size_bytes_from_df", "choose_chunk_size"])
