"""Direction-explicit threshold classification (canonical implementation, LHS 5428192 revision 1).

A threshold row names its limits by direction, so a high-direction critical limit can never be
stored in a low-direction slot (the error found in the submitted implementation, where
CREA (0.6, 1.2, 1.8, None) placed the high critical limit 1.8 in the crit_low position).

Row fields (all optional except authority/analyte/unit):
    low_critical, low_attention, high_attention, high_critical   numeric limits
    low_op  in {"lt", "le"}   comparison used for the low limits  (default "lt")
    high_op in {"ge", "gt"}   comparison used for the high limits (default "ge")
    <limit>_op                optional per-limit override, e.g. low_attention_op = "le"
                              (NICE NG239: B12 < 133 confirmed, 133-258 indeterminate, > 258 unlikely)
"""
from __future__ import annotations

NORMAL, ATTENTION, CRITICAL = "NORMAL", "ATTENTION", "CRITICAL"
LEVEL_RANK = {NORMAL: 0, ATTENTION: 1, CRITICAL: 2}


class SpecError(ValueError):
    pass


def _low(v: float, limit: float, op: str) -> bool:
    return v < limit if op == "lt" else v <= limit


def _high(v: float, limit: float, op: str) -> bool:
    return v >= limit if op == "ge" else v > limit


def validate_row(row: dict) -> None:
    """Reject rows whose limits are not ordered low_critical < low_attention < high_attention < high_critical."""
    for k in ("authority", "analyte", "unit"):
        if not row.get(k):
            raise SpecError(f"missing {k}: {row}")
    for k in ("low_op", "low_critical_op", "low_attention_op"):
        if row.get(k, "lt") not in ("lt", "le"):
            raise SpecError(f"bad operator {k}: {row}")
    for k in ("high_op", "high_critical_op", "high_attention_op"):
        if row.get(k, "ge") not in ("ge", "gt"):
            raise SpecError(f"bad operator {k}: {row}")
    seq = [(k, row.get(k)) for k in ("low_critical", "low_attention", "high_attention", "high_critical")]
    present = [(k, v) for k, v in seq if v is not None]
    if not present:
        raise SpecError(f"no limits: {row}")
    for (k1, v1), (k2, v2) in zip(present, present[1:]):
        if not v1 < v2:
            raise SpecError(f"{row['authority']}/{row['analyte']}: {k1}={v1} must be < {k2}={v2}")


def classify(value: float, row: dict) -> tuple[str, str]:
    """Return (level, direction) with direction in {"high", "low", "none"}."""
    lo, hi = row.get("low_op", "lt"), row.get("high_op", "ge")
    op = lambda k, d: row.get(k + "_op", d)
    if row.get("high_critical") is not None and _high(value, row["high_critical"], op("high_critical", hi)):
        return CRITICAL, "high"
    if row.get("low_critical") is not None and _low(value, row["low_critical"], op("low_critical", lo)):
        return CRITICAL, "low"
    if row.get("high_attention") is not None and _high(value, row["high_attention"], op("high_attention", hi)):
        return ATTENTION, "high"
    if row.get("low_attention") is not None and _low(value, row["low_attention"], op("low_attention", lo)):
        return ATTENTION, "low"
    return NORMAL, "none"
