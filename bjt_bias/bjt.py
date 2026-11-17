"""BJT Common-Emitter DC Bias calculator — engineering logic only.

No Flask imports. All functions operate on BiasInput dataclass and return
plain Python values. Three bias modes are supported (Lab 03):

  divider — voltage-divider bias (Lab 02 behaviour, unchanged)
      primary: solve_thevenin      check: solve_numerical
  fixed   — fixed base bias
      primary: solve_fixed_bias    check: none (no self-consistent loop)
  emitter — emitter bias with a base resistor
      primary: solve_emitter_bias  check: solve_numerical_emitter

All solvers produce the same BiasResult shape; compare_results validates
agreement between the closed-form and numerical paths where both exist.
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
    rb: float = 0.0      # base resistor for fixed / emitter bias (Ω)


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

    def as_lab_dict(self) -> dict[str, object]:
        """Return the shared Lab 03 result dict.

        Voltages are in volts and IC is in milliamps, matching the key names
        suggested by the lab sheet (``vb_v``, ``ve_v``, ``vc_v``, ``vce_v``,
        ``ic_ma``) plus the optional ``warning`` text.
        """
        return {
            "vb_v": self.vb_v,
            "ve_v": self.ve_v,
            "vc_v": self.vc_v,
            "vce_v": self.vce_v,
            "ic_ma": self.ic_a * 1000.0,
            "warning": self.warning,
        }


# ---------------------------------------------------------------------------
# Field names used by the Flask form (must stay in sync with FIELDS)
# ---------------------------------------------------------------------------

FIELDS: Tuple[str, ...] = (
    "vcc", "r1", "r2", "rc", "re", "beta", "vbe",
)

#: Bias modes supported by the app.  ``divider`` is the default so the
#: Lab 02 form keeps working unchanged.
MODES: Tuple[str, ...] = ("divider", "fixed", "emitter")

#: Form fields required by each mode.  Only these are parsed and validated;
#: fields that do not belong to the selected circuit are ignored.
MODE_FIELDS: dict[str, Tuple[str, ...]] = {
    "divider": FIELDS,
    "fixed": ("vcc", "rb", "rc", "beta", "vbe"),
    "emitter": ("vcc", "rb", "re", "rc", "beta", "vbe"),
}

MODE_ERROR = "โหมดไบอัสไม่ถูกต้อง"


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

def validate_inputs(inp: BiasInput, mode: str = "divider") -> dict[str, str]:
    """Validate a BiasInput for the selected mode.

    Returns a dict of error messages keyed by field (empty when valid).
    This function does NOT raise; callers should check the returned dict.
    Only fields required by ``mode`` are checked, so a fixed-bias circuit is
    not rejected for having no R1/R2/RE.
    """
    if mode not in MODE_FIELDS:
        return {"mode": MODE_ERROR}

    errors: dict[str, str] = {}
    required = MODE_FIELDS[mode]

    # --- VCC --------------------------------------------------------------
    if inp.vcc <= 0:
        errors["vcc"] = "ต้องมากกว่า 0"

    # --- Resistances used by this mode -----------------------------------
    for fname, fval in [
        ("r1", inp.r1),
        ("r2", inp.r2),
        ("rc", inp.rc),
        ("re", inp.re),
        ("rb", inp.rb),
    ]:
        if fname in required and fval <= 0:
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

def parse_inputs(
    raw: Mapping[str, object],
    mode: str = "divider",
) -> tuple[BiasInput, ValidationError]:
    """Convert raw form values into a BiasInput for the selected mode.

    Returns (bias_input, validation_error).  If validation passes,
    validation_error.errors is an empty dict; otherwise the function raises
    ValidationError.

    Only the fields required by ``mode`` are read.  An unknown mode raises
    ValidationError instead of silently falling back to divider bias.

    The function RAISES ValidationError when any error is found;
    callers should use ``try / except ValidationError``.
    """
    if mode not in MODE_FIELDS:
        raise ValidationError({"mode": MODE_ERROR})

    errors: dict[str, str] = {}

    # ------------------------------------------------------------------
    # 1) Basic key presence & type coercion (mode-specific fields only)
    # ------------------------------------------------------------------
    converted: dict[str, float] = {}
    for name in MODE_FIELDS[mode]:
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
        r1=converted.get("r1", 0.0),
        r2=converted.get("r2", 0.0),
        rc=converted["rc"],
        re=converted.get("re", 0.0),
        beta=converted["beta"],
        vbe=converted["vbe"],
        rb=converted.get("rb", 0.0),
    )

    # ------------------------------------------------------------------
    # 4) Run rule‑level validation — may raise ValidationError
    # ------------------------------------------------------------------
    rule_errors = validate_inputs(inp, mode)  # returns dict, may be non-empty

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
# Fixed-bias solver (Lab 03)
# ---------------------------------------------------------------------------

def _make_result(
    vbb_v: float,
    rb_ohm: float,
    ib: float,
    ic: float,
    ie: float,
    vce: float,
    vb: float,
    ve: float,
    vc: float,
    vcc: float,
) -> BiasResult:
    """Classify a solved operating point and build a BiasResult.

    Shared by the fixed- and emitter-bias solvers so their region/warning
    behaviour matches the divider solver exactly.
    """
    if ib <= 0:
        return BiasResult(
            vbb_v=vbb_v,
            rb_ohm=rb_ohm,
            ib_a=0.0,
            ic_a=0.0,
            ie_a=0.0,
            vce_v=float(vcc),
            vb_v=vbb_v,
            ve_v=0.0,
            vc_v=float(vcc),
            region="cutoff",
            warning="ทรานซิสเตอร์อยู่ในย่านคัตออฟ (IB = 0) — ไม่มีกระแสสะสม",
        )

    if vce <= VCE_SAT_V:
        return BiasResult(
            vbb_v=vbb_v,
            rb_ohm=rb_ohm,
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

    return BiasResult(
        vbb_v=vbb_v,
        rb_ohm=rb_ohm,
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


def solve_fixed_bias(inp: BiasInput) -> BiasResult:
    """Fixed base bias: IB = (VCC - VBE) / RB, with the emitter grounded.

    VBB is the supply seen through RB, so the Thevenin note reports
    VBB = VCC and RB = RB.  There is no emitter resistor, hence VE = 0.
    """
    ib = (inp.vcc - inp.vbe) / inp.rb
    ic = inp.beta * ib
    ie = (1 + inp.beta) * ib

    ve = 0.0
    vc = inp.vcc - ic * inp.rc
    vb = inp.vbe
    vce = vc - ve

    return _make_result(
        vbb_v=inp.vcc,
        rb_ohm=inp.rb,
        ib=ib,
        ic=ic,
        ie=ie,
        vce=vce,
        vb=vb,
        ve=ve,
        vc=vc,
        vcc=inp.vcc,
    )


# ---------------------------------------------------------------------------
# Emitter-bias solver (Lab 03)
# ---------------------------------------------------------------------------

def solve_emitter_bias(inp: BiasInput) -> BiasResult:
    """Emitter bias: IB = (VCC - VBE) / (RB + (1 + beta) RE)."""
    ib = (inp.vcc - inp.vbe) / (inp.rb + (1 + inp.beta) * inp.re)
    ic = inp.beta * ib
    ie = (1 + inp.beta) * ib

    ve = ie * inp.re
    vc = inp.vcc - ic * inp.rc
    vb = ve + inp.vbe
    vce = vc - ve

    return _make_result(
        vbb_v=inp.vcc,
        rb_ohm=inp.rb,
        ib=ib,
        ic=ic,
        ie=ie,
        vce=vce,
        vb=vb,
        ve=ve,
        vc=vc,
        vcc=inp.vcc,
    )


def _emitter_base_kcl(inp: BiasInput, vb: float) -> float:
    """KCL at the base node for emitter bias.

    f(VB) = (VCC - VB)/RB - max(0, VB - VBE)/((1 + beta) RE)

    Strictly decreasing on [0, VCC], so bisection converges.
    """
    ib = max(0.0, vb - inp.vbe) / ((1 + inp.beta) * inp.re)
    return (inp.vcc - vb) / inp.rb - ib


def solve_numerical_emitter(inp: BiasInput) -> BiasResult:
    """Independent bisection check for emitter bias (does not use the
    closed-form IB equation directly)."""
    low, high = 0.0, inp.vcc
    for _ in range(200):
        mid = (low + high) / 2
        if _emitter_base_kcl(inp, mid) > 0:
            low = mid
        else:
            high = mid
    vb_node = (low + high) / 2

    ib = max(0.0, vb_node - inp.vbe) / ((1 + inp.beta) * inp.re)
    ic = inp.beta * ib
    ie = (1 + inp.beta) * ib

    ve = ie * inp.re
    vc = inp.vcc - ic * inp.rc
    vce = vc - ve

    return _make_result(
        vbb_v=inp.vcc,
        rb_ohm=inp.rb,
        ib=ib,
        ic=ic,
        ie=ie,
        vce=vce,
        vb=ve + inp.vbe,
        ve=ve,
        vc=vc,
        vcc=inp.vcc,
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

def analyze_divider(inp: BiasInput) -> dict[str, object]:
    """Voltage-divider analysis: Thevenin primary + numerical check."""
    primary = solve_thevenin(inp)
    check = solve_numerical(inp)
    return {
        "primary": primary,
        "check": check,
        "comparison": compare_results(primary, check),
    }


def analyze_fixed(inp: BiasInput) -> dict[str, object]:
    """Fixed-bias analysis: no independent cross-check exists."""
    return {"primary": solve_fixed_bias(inp), "check": None, "comparison": None}


def analyze_emitter(inp: BiasInput) -> dict[str, object]:
    """Emitter-bias analysis: closed form + bisection KCL check."""
    primary = solve_emitter_bias(inp)
    check = solve_numerical_emitter(inp)
    return {
        "primary": primary,
        "check": check,
        "comparison": compare_results(primary, check),
    }


def analyze(inp: BiasInput, mode: str = "divider") -> dict[str, object]:
    """Produce a complete analysis dict for a given BiasInput and mode.

    The returned dict always has three top‑level keys:
      primary    — BiasResult from the selected mode's closed-form solver
      check      — independent BiasResult, or None when the mode has no
                   meaningful self-consistent cross-check (fixed bias)
      comparison — dict from compare_results, or None when check is None

    ``divider`` is the default so the Lab 02 API keeps working unchanged.
    """
    if mode == "divider":
        return analyze_divider(inp)
    elif mode == "fixed":
        return analyze_fixed(inp)
    elif mode == "emitter":
        return analyze_emitter(inp)
    raise ValidationError({"mode": MODE_ERROR})