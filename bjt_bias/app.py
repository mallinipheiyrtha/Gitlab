"""Flask web app for BJT Common-Emitter DC Bias calculation.

Serves a single page with a form and result display. All engineering
logic lives in `bjt_bias.bjt` — this module imports nothing from Flask.
"""

from flask import Flask, render_template, request

from .bjt import (
    FIELDS,
    ValidationError,
    parse_inputs,
    analyze,
    BiasInput,
)


app = Flask(__name__)

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