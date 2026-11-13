"""BJT Common-Emitter DC Bias calculator — engineering logic only.

No Flask imports. All functions operate on BiasInput dataclass and return
plain Python values. Two solver paths are provided:
  1) solve_thevenin  — closed-form Thevenin equivalent (spec primary)
  2) solve_numerical — bisection KCL check (independent verification)

Both produce the same BiasResult shape; compare_results validates agreement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Tuple, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VCE_SAT_V = 0.2  # V  — saturation threshold voltage


# ---------------------------------------------------------------------------
# Exception used for input validation errors
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    """Raised when input validation fails.  Holds per-field error messages."""

    def __init__(self, errors: dict[str, str] | None = None) -> None:
        super().__init__(str(errors) if errors else "")
        self.errors: dict[str, str] = errors if errors is not None else {}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BiasInput:
    """Immutable container for BJT bias design inputs."""

    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


@dataclass(frozen=True)
class BiasResult:
    """Result of a DC bias calculation."""

    vbb_v: float          # Thevenin base voltage (V)
    rb_ohm: float         # Thevenin base resistance (Ω)
    ib_a: float           # Base current (A)
    ic_a: float           # Collector current (A)
    ie_a: float           # Emitter current (A)
    vce_v: float          # Collector-emitter voltage (V)
    vb_v: float           # Base node voltage (V)
    ve_v: float           # Emitter node voltage (V)
    vc_v: float           # Collector node voltage (V)
    region: str           # "active" | "saturation" | "cutoff"
    warning: Optional[str]  # Human-readable warning, or None


# ---------------------------------------------------------------------------
# Field names used by the Flask form (must stay in sync with FIELDS)
# ---------------------------------------------------------------------------

FIELDS: Tuple[str, ...] = (
    "vcc", "r1", "r2", "rc", "re", "beta", "vbe",
)


# ---------------------------------------------------------------------------
# Validation helpers (pure functions that raise ValidationError)
# ---------------------------------------------------------------------------

def _check_positive(name: str, val: float, msg: str) -> None:
    """Ensure val > 0; raise ValidationError otherwise."""
    if val <= 0:
        raise ValidationError({name: msg})


def _check_range(name: str, val: float, lo: float, hi: float, msg_lo: str, msg_hi: str) -> None:
    """Ensure lo < val < hi; raise ValidationError otherwise."""
    if val <= lo:
        raise ValidationError({name: msg_lo})
    if val >= hi:
        raise ValidationError({name: msg_hi})


# ---------------------------------------------------------------------------
# Public validation entry point (used by solver, not by parse_inputs)
# ---------------------------------------------------------------------------

def validate_inputs(inp: BiasInput) -> dict[str, str]:
    """Validate a BiasInput and return a dict of error messages keyed by field.

    Returns empty dict if validation passes.
    This function does NOT raise; callers should check the returned dict.
    """
    errors: dict[str, str] = {}

    # --- VCC --------------------------------------------------------------
    if inp.vcc <= 0:
        errors["vcc"] = "ต้องมากกว่า 0"

    # --- R1, R2, RC, RE -------------------------------------------------
    for fname, fval in [
        ("r1", inp.r1),
        ("r2", inp.r2),
        ("rc", inp.rc),
        ("re", inp.re),
    ]:
        if fval <= 0:
            errors[fname] = "ต้องมากกว่า 0"

    # --- beta -------------------------------------------------------------
    if inp.beta <= 0:
        errors["beta"] = "ต้องมากกว่า 0"

    # --- VBE --------------------------------------------------------------
    # VBE must be in (0, VCC).  If VCC <= 0 this is already caught above.
    if inp.vcc > 0:
        if inp.vbe <= 0:
            errors["vbe"] = "ต้องมากกว่า 0"
        elif inp.vbe >= inp.vcc:
            errors["vbe"] = "ต้องน้อยกว่า VCC"
    else:
        # VCC already <= 0; still report VBE range errors
        if inp.vbe <= 0:
            errors["vbe"] = "ต้องมากกว่า 0"
        elif inp.vbe >= inp.vcc:
            errors["vbe"] = "ต้องน้อยกว่า VCC"

    return errors


# ---------------------------------------------------------------------------
# Raw‑form parsing / conversion
# ---------------------------------------------------------------------------

def parse_inputs(raw: Mapping[str, object]) -> tuple[BiasInput, ValidationError]:
    """Convert raw form values into a BiasInput, performing validation.

    Returns (bias_input, validation_error).  If validation passes,
    validation_error.errors is an empty dict; otherwise the function raises
    ValidationError.

    The function RAISES ValidationError when any error is found;
    callers should use ``try / except ValidationError``.
    """
    errors: dict[str, str] = {}

    # ------------------------------------------------------------------
    # 1) Basic key presence & type coercion
    # ------------------------------------------------------------------
    converted: dict[str, float] = {}
    for name in FIELDS:
        if name not in raw:
            errors[name] = "กรุณากรอกค่านี้"
            continue
        raw_val = raw[name]
        # Empty string / None / empty whitespace
        if raw_val is None or (isinstance(raw_val, str) and raw_val.strip() == ""):
            errors[name] = "กรุณากรอกค่านี้"
            continue
        # Try to convert to float — catch ValueError / TypeError
        try:
            f = float(raw_val)
        except (ValueError, TypeError):
            errors[name] = "ต้องเป็นตัวเลข"
            continue
        # Finite check
        if not math.isfinite(f):
            errors[name] = "ต้องเป็นตัวเลขจำกัด"
            continue
        converted[name] = f

    # ------------------------------------------------------------------
    # 2) If any structural errors exist, raise ValidationError now
    # ------------------------------------------------------------------
    if errors:
        raise ValidationError(errors)

    # ------------------------------------------------------------------
    # 3) Build BiasInput
    # ------------------------------------------------------------------
    inp = BiasInput(
        vcc=converted["vcc"],
        r1=converted["r1"],
        r2=converted["r2"],
        rc=converted["rc"],
        re=converted["re"],
        beta=converted["beta"],
        vbe=converted["vbe"],
    )

    # ------------------------------------------------------------------
    # 4) Run rule‑level validation — may raise ValidationError
    # ------------------------------------------------------------------
    rule_errors = validate_inputs(inp)  # returns dict, may be non-empty

    # ------------------------------------------------------------------
    # 5) If validation found problems, raise
    # ------------------------------------------------------------------
    if rule_errors:
        raise ValidationError(rule_errors)

    # ------------------------------------------------------------------
    # 6) All good — return input with empty error dict
    # ------------------------------------------------------------------
    return inp, ValidationError({})


# ---------------------------------------------------------------------------
# Thevenin closed-form solver (primary method)
# ---------------------------------------------------------------------------

def solve_thevenin(inp: BiasInput) -> BiasResult:
    """Calculate DC operating point using the Thevenin equivalent formula.

    Returns a BiasResult with region classification and optional warning.
    """
    # VBB = VCC * R2 / (R1 + R2)
    vbb = inp.vcc * inp.r2 / (inp.r1 + inp.r2)
    # RB = R1 || R2
    rb = (inp.r1 * inp.r2) / (inp.r1 + inp.r2)

    # IB = (VBB - VBE) / (RB + (1 + beta) * RE)
    ib = (vbb - inp.vbe) / (rb + (1 + inp.beta) * inp.re)

    # IC = beta * IB
    ic = inp.beta * ib
    # IE = (1 + beta) * IB
    ie = (1 + inp.beta) * ib

    # VCE = VCC - IC * RC - IE * RE
    vce = inp.vcc - ic * inp.rc - ie * inp.re

    # Node voltages: VE = IE·RE, VC = VCC − IC·RC, VB = VE + VBE
    ve = ie * inp.re
    vc = inp.vcc - ic * inp.rc
    vb = ve + inp.vbe

    # Region classification
    if ib <= 0:
        # Cutoff: no current flows, base is fixed by the divider and the
        # collector sits at VCC; VCE = VC - VE = VCC.
        return BiasResult(
            vbb_v=vbb,
            rb_ohm=rb,
            ib_a=0.0,
            ic_a=0.0,
            ie_a=0.0,
            vce_v=float(inp.vcc),
            vb_v=vbb,
            ve_v=0.0,
            vc_v=float(inp.vcc),
            region="cutoff",
            warning="ทรานซิสเตอร์อยู่ในย่านคัตออฟ (IB = 0) — ไม่มีกระแสสะสม",
        )

    # Active / saturation boundary
    if vce <= VCE_SAT_V:
        # Saturation: report the active‑model values but flag the warning
        return BiasResult(
            vbb_v=vbb,
            rb_ohm=rb,
            ib_a=ib,
            ic_a=ic,
            ie_a=ie,
            vce_v=vce,
            vb_v=vb,
            ve_v=ve,
            vc_v=vc,
            region="saturation",
            warning="ทรานซิสเตอร์อยู่ในย่านแซทเทอเรชัน (VCE ≤ 0.2 V) — ค่าที่ได้จากสมการแอกทีฟใช้ไม่ได้จริง",
        )

    # Active region
    return BiasResult(
        vbb_v=vbb,
        rb_ohm=rb,
        ib_a=ib,
        ic_a=ic,
        ie_a=ie,
        vce_v=vce,
        vb_v=vb,
        ve_v=ve,
        vc_v=vc,
        region="active",
        warning=None,
    )


# ---------------------------------------------------------------------------
# Independent numerical solver (bisection on KCL at base node)
# ---------------------------------------------------------------------------

def _base_kcl(inp: BiasInput, vb: float) -> float:
    """KCL at the base node for the voltage‑divider bias.

    f(VB) = (VCC - VB)/R1 - VB/R2 - max(0, VB - VBE)/((1+beta)RE)

    The function is strictly decreasing on [0, VCC], so bisection converges.
    """
    ib = max(0.0, vb - inp.vbe) / ((1 + inp.beta) * inp.re)
    return (inp.vcc - vb) / inp.r1 - vb / inp.r2 - ib


def solve_numerical(inp: BiasInput) -> BiasResult:
    """Calculate DC operating point using bisection (self‑consistent KCL).

    This is an independent check that does NOT use the closed‑form Thevenin
    formulas.  It converges to the unique base voltage VB that satisfies KCL,
    then derives IB, IC, IE, VCE from that VB.
    """
    # Bisection on VB in [0, VCC]
    low, high = 0.0, inp.vcc
    for _ in range(200):
        mid = (low + high) / 2
        if _base_kcl(inp, mid) > 0:
            low = mid
        else:
            high = mid
    vb = (low + high) / 2

    # From the found VB, compute currents and voltage
    ib = max(0.0, vb - inp.vbe) / ((1 + inp.beta) * inp.re)
    ic = inp.beta * ib
    ie = (1 + inp.beta) * ib
    vce = inp.vcc - ic * inp.rc - ie * inp.re

    # Node voltages follow the same equations as the Thevenin path
    ve = ie * inp.re
    vc = inp.vcc - ic * inp.rc
    vb_node = ve + inp.vbe
    vbb = inp.vcc * inp.r2 / (inp.r1 + inp.r2)

    # Re-use the same region logic as solve_thevenin
    if ib <= 0:
        return BiasResult(
            vbb_v=vbb,
            rb_ohm=(inp.r1 * inp.r2) / (inp.r1 + inp.r2),
            ib_a=0.0,
            ic_a=0.0,
            ie_a=0.0,
            vce_v=float(inp.vcc),
            vb_v=vbb,
            ve_v=0.0,
            vc_v=float(inp.vcc),
            region="cutoff",
            warning="ทรานซิสเตอร์อยู่ในย่านคัตออฟ (IB = 0) — ไม่มีกระแสสะสม",
        )

    if vce <= VCE_SAT_V:
        return BiasResult(
            vbb_v=vbb,
            rb_ohm=(inp.r1 * inp.r2) / (inp.r1 + inp.r2),
            ib_a=ib,
            ic_a=ic,
            ie_a=ie,
            vce_v=vce,
            vb_v=vb_node,
            ve_v=ve,
            vc_v=vc,
            region="saturation",
            warning="ทรานซิสเตอร์อยู่ในย่านแซทเทอเรชัน (VCE ≤ 0.2 V) — ค่าที่ได้จากสมการแอกทีฟใช้ไม่ได้จริง",
        )

    return BiasResult(
        vbb_v=vbb,
        rb_ohm=(inp.r1 * inp.r2) / (inp.r1 + inp.r2),
        ib_a=ib,
        ic_a=ic,
        ie_a=ie,
        vce_v=vce,
        vb_v=vb_node,
        ve_v=ve,
        vc_v=vc,
        region="active",
        warning=None,
    )


# ---------------------------------------------------------------------------
# Cross‑check / comparison
# ---------------------------------------------------------------------------

def compare_results(
    primary: BiasResult,
    check: BiasResult,
    rel_tol: float = 1e-6,
) -> dict[str, object]:
    """Compare two BiasResult objects and report agreement.

    Agreement means that both IC and VCE are within the given relative
    tolerance (with an absolute floor of 1e-9) for both quantities.

    Returns a dict with keys:
      agrees — bool
      delta_ic_a — absolute difference in collector current (A)
      delta_vce_v — absolute difference in collector-emitter voltage (V)
    """
    delta_ic_a = abs(primary.ic_a - check.ic_a)
    delta_vce_v = abs(primary.vce_v - check.vce_v)

    ic_ok = delta_ic_a <= max(1e-9, rel_tol * max(abs(primary.ic_a), abs(check.ic_a)))
    vce_ok = delta_vce_v <= max(1e-9, rel_tol * max(abs(primary.vce_v), abs(check.vce_v)))

    agrees = ic_ok and vce_ok
    return {
        "agrees": agrees,
        "delta_ic_a": delta_ic_a,
        "delta_vce_v": delta_vce_v,
    }


# ---------------------------------------------------------------------------
# High‑level convenience wrapper
# ---------------------------------------------------------------------------

def analyze(inp: BiasInput) -> dict[str, object]:
    """Produce a complete analysis dict for a given BiasInput.

    The returned dict has three top‑level keys:
      primary  — result from solve_thevenin
      check    — result from solve_numerical
      comparison — dict from compare_results(primary, check)
    """
    primary = solve_thevenin(inp)
    check = solve_numerical(inp)
    comparison = compare_results(primary, check)
    return {"primary": primary, "check": check, "comparison": comparison}