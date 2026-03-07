from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Optional, Tuple

import numpy as np
import pandas as pd


def _safe_float(x: Any) -> Optional[float]:
    try:
        v = float(x)
        if np.isnan(v):
            return None
        return v
    except Exception:
        return None


def _step_to_decimals(step_str: str) -> Optional[int]:
    s = (step_str or "").strip()
    if not s or s.lower() == "auto":
        return None
    if "." in s:
        return max(len(s.split(".", 1)[1]), 0)
    return 0


def _quantize_decimal(value: float, step_str: str) -> float:
    s = (step_str or "").strip()
    if not s or s.lower() == "auto":
        return value
    try:
        step = Decimal(s)
        d = Decimal(str(value))
        if step == 0:
            return value
        q = d / step
        q_round = q.to_integral_value(rounding=ROUND_HALF_UP)
        out = q_round * step
        return float(out)
    except (InvalidOperation, ValueError):
        return value


def get_precision_step(mode: str, digits: Optional[int]) -> str:
    m = (mode or "auto").strip().lower()
    if m == "auto":
        return "auto"
    d = int(digits or 0)
    if d < 0:
        d = 0
    if m in {"decimal", "dp", "fraction"}:
        if d == 0:
            return "1"
        return "0." + ("0" * (d - 1)) + "1"
    if m in {"integer", "int"}:
        return str(10**d)
    return "auto"


def parse_precision_step(step: str) -> Tuple[str, int]:
    s = (step or "").strip().lower()
    if not s or s == "auto":
        return "auto", 0
    if "." in s:
        frac = s.split(".", 1)[1]
        return "decimal", max(len(frac), 0)
    try:
        n = int(Decimal(s))
        if n <= 1:
            return "decimal", 0
        digits = len(str(abs(n))) - 1
        return "integer", max(digits, 0)
    except Exception:
        return "auto", 0


def resolve_precision_step(params: Optional[dict]) -> str:
    p = params or {}
    if "boundary_precision" in p:
        return str(p.get("boundary_precision") or "auto")
    mode = str(p.get("boundary_precision_mode") or "auto")
    digits = p.get("boundary_precision_digits", 0)
    try:
        digits_i = int(digits)
    except Exception:
        digits_i = 0
    return get_precision_step(mode, digits_i)


def snap_value_to_precision(
    value: Any,
    *,
    precision_mode: str,
    precision_digits: int,
) -> Any:
    v = _safe_float(value)
    if v is None:
        return value
    if np.isinf(v):
        return v
    step_in_unit = get_precision_step(precision_mode, precision_digits)
    if (step_in_unit or "").strip().lower() == "auto":
        return v
    return float(_quantize_decimal(v, step_in_unit))


def format_number(
    value: Any,
    *,
    precision: str = "auto",
) -> str:
    v = _safe_float(value)
    if v is None:
        return str(value)
    if np.isneginf(v):
        return "-∞"
    if np.isposinf(v):
        return "+∞"

    scaled = _quantize_decimal(v, precision)

    decimals = _step_to_decimals(precision)
    if decimals is None:
        s = f"{scaled:.6g}"
    else:
        s = f"{scaled:.{decimals}f}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")

    return f"{s}"


def format_interval(
    interval: Any,
    *,
    precision: str = "auto",
) -> str:
    if isinstance(interval, pd.Interval):
        left = format_number(interval.left, precision=precision)
        right = format_number(interval.right, precision=precision)
        return f"({left}, {right}]"
    return str(interval)


def format_bin_label(
    bin_value: Any,
    *,
    precision: str = "auto",
) -> str:
    if isinstance(bin_value, pd.Interval):
        return format_interval(bin_value, precision=precision)
    return str(bin_value)
