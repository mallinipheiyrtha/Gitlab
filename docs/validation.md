# Lab 03 — Browser Acceptance Record (A1–A5)

- **Date:** 2026-11-17
- **App:** BJT DC Bias Web App, served at `http://127.0.0.1:5000`
- **Browser tool actually used:** **OpenCode Browser** (in-app Chromium, real form
  fill + submit). Playwright MCP was **not** used because Node/npx are not
  installed in this environment.
- **Shared inputs for every case:** VCC = 12 V, RC = 2.2 kΩ, β = 100,
  VBE = 0.70 V.
- **Tolerance:** IC ±0.01 mA, VCE ±0.02 V.

## Results table

| # | Mode | Case-specific inputs | Expected IC | Expected VCE | Observed IC | Observed VCE | Units | Method | Status | Evidence |
|---|------|----------------------|-------------|--------------|-------------|--------------|-------|--------|--------|----------|
| A1 | Voltage Divider Bias | R1 = 100 kΩ, R2 = 22 kΩ, RE = 1 kΩ | 1.230 mA | 8.052 V | **1.23 mA** | **8.052 V** | mA / V | OpenCode Browser | PASS | [a1.png](evidence/a1.png) |
| A2 | Fixed Bias | RB = 1 MΩ | 1.130 mA | 9.514 V | **1.13 mA** | **9.514 V** | mA / V | OpenCode Browser | PASS | [a2.png](evidence/a2.png) |
| A3 | Emitter Bias | RB = 1 MΩ, RE = 1 kΩ | 1.026 mA | 8.705 V | **1.026 mA** | **8.705 V** | mA / V | OpenCode Browser | PASS | [a3.png](evidence/a3.png) |
| A4 | Emitter Bias | RB = 1 MΩ, RE = 2 kΩ | 0.940 mA | 8.033 V | **940.1 µA (0.9401 mA)** | **8.033 V** | mA / V | OpenCode Browser | PASS | [a4.png](evidence/a4.png) |
| A5 | Fixed Bias | RB = 0 Ω (invalid) | — | — | Error shown: `ต้องมากกว่า 0`; no results section | — | — | OpenCode Browser | PASS | [a5.png](evidence/a5.png) |

### Observed node voltages (from the same browser runs)

| # | VB | VE | VC | VCE | IB | IC | IE |
|---|----|----|----|-----|----|----|----|
| A1 | 1.942 V | 1.242 V | 9.294 V | 8.052 V | 12.299 µA | 1.23 mA | 1.242 mA |
| A2 | 700 mV | 0 V | 9.514 V | 9.514 V | 11.3 µA | 1.13 mA | 1.141 mA |
| A3 | 1.737 V | 1.037 V | 9.742 V | 8.705 V | 10.263 µA | 1.026 mA | 1.037 mA |
| A4 | 2.599 V | 1.899 V | 9.932 V | 8.033 V | 9.401 µA | 940.1 µA | 949.501 µA |

### A4 trend check

A3 → A4 increases RE from 1 kΩ to 2 kΩ while every other value stays fixed.
IC falls from **1.026 mA** to **0.9401 mA**, which is the expected direction:
a larger emitter resistor increases the denominator
`RB + (1 + β)RE` and therefore reduces IB and IC.

### A5 error check

Submitting Fixed Bias with `RB = 0` returns the form with:

- field error on RB: `ต้องมากกว่า 0`
- mode-labelled alert: `พบข้อผิดพลาดในโหมด Fixed Bias`
- **no** `DC Bias Results` section
- HTTP 200 and the page keeps working (no crash)

The server also rejects an unknown `mode` value with HTTP 400 instead of
silently calculating voltage-divider bias.

## Independent reference calculation (new mode: Emitter Bias)

`docs/reference_emitter.py` recomputes A3/A4 **without importing**
`bjt_bias`. It solves the base-node equation

```
(VCC − VB) / RB = (VB − VBE) / ((1 + β) RE)
```

with exact rational arithmetic (`fractions.Fraction`) and then derives the
currents and node voltages from Ohm's law.

Command and output:

```text
> py -3.7 docs/reference_emitter.py
A3 (RE = 1000 ohm)
  VB  = 1.736603 V
  VE  = 1.036603 V
  VC  = 9.742053 V
  VCE = 8.705450 V
  IB  = 0.000010263 A
  IC  = 0.001026340 A = 1.0263 mA
  IE  = 0.001036603 A
A4 (RE = 2000 ohm)
  VB  = 2.599002 V
  VE  = 1.899002 V
  VC  = 9.931780 V
  VCE = 8.032779 V
  IB  = 0.000009401 A
  IC  = 0.000940100 A = 0.9401 mA
  IE  = 0.000949501 A
```

The reference values agree with the browser observations well inside the
±0.01 mA / ±0.02 V tolerance.

## Regression tests

The existing automated tests were kept unchanged (the lab sheet asks for no
new unittest or Playwright script):

```text
> py -3.7 -m pytest bjt_bias/tests test_flask.py -q
46 passed
```
