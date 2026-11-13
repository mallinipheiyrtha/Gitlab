"""Flask web app for BJT Common-Emitter DC Bias calculation.

Serves a single page with a form and result display. All engineering
logic lives in `bjt_bias.bjt` — this module imports nothing from Flask.
"""

import math

from flask import Flask, render_template, request

from .bjt import (
    FIELDS,
    ValidationError,
    parse_inputs,
    analyze,
    BiasInput,
)


app = Flask(__name__)


@app.template_filter("ohm")
def format_ohm(raw: object) -> str:
    """Format a raw resistance value for display in the circuit diagram.

    Values come straight from the form, so they may be missing, empty, or
    non-numeric; those render as an em dash instead of raising. The value is
    rounded to six significant digits *before* the unit is chosen, so
    ``999999.5`` becomes ``1 MΩ`` instead of ``1000 kΩ``.
    """
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(value):
        return "—"
    rounded = float(f"{value:.6g}")
    if rounded >= 1_000_000:
        return f"{_trim(rounded / 1_000_000)} MΩ"
    if rounded >= 1_000:
        return f"{_trim(rounded / 1_000)} kΩ"
    return f"{_trim(rounded)} Ω"


def _trim(number: float) -> str:
    """Drop trailing zeros in the fractional part without touching the integer."""
    whole, frac = f"{number:.6f}".split(".")
    frac = frac.rstrip("0")
    return f"{whole}.{frac}" if frac else whole


# Engineering prefixes, largest first. The tuple is scanned for the first
# factor that keeps the magnitude at or above 1.
SI_PREFIXES = (
    (1e9, "G"),
    (1e6, "M"),
    (1e3, "k"),
    (1.0, ""),
    (1e-3, "m"),
    (1e-6, "µ"),
    (1e-9, "n"),
    (1e-12, "p"),
)


@app.template_filter("si")
def format_si(value: object, unit: str) -> str:
    """Format a value with an SI engineering prefix and up to 3 decimals.

    ``12.298e-6`` A becomes ``12.298 µA``; zero and non-finite values fall
    back to the base unit / an em dash. Negative values keep their sign but
    use the Unicode minus (U+2212) for typographic consistency.
    """
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(number):
        return "—"
    if number == 0:
        return f"0 {unit}"

    magnitude = abs(number)
    factor, prefix = SI_PREFIXES[-1]
    for candidate_factor, candidate_prefix in SI_PREFIXES:
        if magnitude / candidate_factor >= 1:
            factor, prefix = candidate_factor, candidate_prefix
            break

    scaled = f"{number / factor:.3f}".rstrip("0").rstrip(".")
    if scaled.startswith("-"):
        scaled = "−" + scaled[1:]
    return f"{scaled} {prefix}{unit}"

#: Default values used when the page loads via GET /
DEFAULTS = {
    "vcc": "12",
    "r1": "47000",
    "r2": "10000",
    "rc": "4700",
    "re": "1000",
    "beta": "100",
    "vbe": "0.7",
}


@app.get("/")
def index():
    """Render the form page (no results yet)."""
    return render_template(
        "index.html",
        values=DEFAULTS,
        errors={},
        analysis=None,
    )


@app.post("/calculate")
def calculate():
    """Process the form submission, validate, compute, and re‑render."""

    # Collect raw string values from the form
    raw_values = {name: request.form.get(name, "") for name in FIELDS}

    try:
        bias_input, parse_err = parse_inputs(raw_values)
    except ValidationError as ve:
        # Re‑display the form with per‑field messages
        return render_template(
            "index.html",
            values=raw_values,
            errors=ve.errors,
            analysis=None,
        )

    # All input is valid — perform the full engineering analysis
    analysis = analyze(bias_input)  # {"primary": ..., "check": ..., "comparison": ...}

    # Pass the original values back so the form keeps what the user typed
    return render_template(
        "index.html",
        values=raw_values,
        errors={},
        analysis=analysis,
    )