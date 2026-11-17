"""Independent reference calculation for Lab 03 — Emitter Bias (A3/A4).

This script deliberately does NOT import ``bjt_bias``.  It solves the base
node equation with exact rational arithmetic (``fractions.Fraction``):

    (VCC - VB) / RB = (VB - VBE) / ((1 + beta) * RE)

Rearranged and solved for VB, then the currents and node voltages follow
from Ohm's law.  Exact fractions avoid floating-point rounding, so the
printed decimals are a genuinely independent reference for A3 and A4.

Run from the repository root:

    py -3.7 docs/reference_emitter.py
"""

from fractions import Fraction as F


def emitter(vcc, rb, rc, re, beta, vbe):
    """Return (VB, VE, VC, VCE, IB, IC, IE) as exact Fractions."""
    vcc, rb, rc, re, beta, vbe = map(F, (vcc, rb, rc, re, beta, vbe))
    g = (1 + beta) * re  # (1 + beta) RE

    # (VCC - VB)/RB = (VB - VBE)/g
    # VB * (1/RB + 1/g) = VCC/RB + VBE/g
    vb = (vcc / rb + vbe / g) / (F(1) / rb + F(1) / g)

    ib = (vb - vbe) / g
    ic = beta * ib
    ie = (1 + beta) * ib

    ve = ie * re
    vc = vcc - ic * rc
    vce = vc - ve
    return vb, ve, vc, vce, ib, ic, ie


def main():
    shared = dict(vcc=12, rb=1_000_000, rc=2_200, beta=100, vbe=F(7, 10))
    for name, re in (("A3", 1_000), ("A4", 2_000)):
        vb, ve, vc, vce, ib, ic, ie = emitter(re=re, **shared)
        print(name, "(RE = %d ohm)" % re)
        print("  VB  = %.6f V" % float(vb))
        print("  VE  = %.6f V" % float(ve))
        print("  VC  = %.6f V" % float(vc))
        print("  VCE = %.6f V" % float(vce))
        print("  IB  = %.9f A" % float(ib))
        print("  IC  = %.9f A = %.4f mA" % (float(ic), float(ic) * 1000))
        print("  IE  = %.9f A" % float(ie))


if __name__ == "__main__":
    main()
