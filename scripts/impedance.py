"""Controlled-impedance geometry for JLC04161H-7628 (outer layer L1 over L2 GND).
Closed-form models: Hammerstad-Jensen microstrip (+thickness correction), IPC-2141A edge-coupled
differential approximation, Wadell grounded-CPW (conformal mapping). Expect +-5 %; confirm in the
JLCPCB impedance calculator before ordering (soldermask lowers Z by ~1-3 ohm)."""
import math
from scipy.special import ellipk
from scipy.optimize import brentq

H = 0.2104      # mm, 7628 prepreg L1-L2
T = 0.035       # mm, 1 oz finished outer copper
ER = 4.4        # 7628 prepreg Dk


def microstrip(w, h=H, t=T, er=ER):
    w_eff = w + (t / math.pi) * (1 + math.log(4 * math.e / math.sqrt((t / h) ** 2 + (1 / math.pi / (w / t + 1.1)) ** 2)))
    u = w_eff / h
    a = 1 + math.log((u**4 + (u / 52) ** 2) / (u**4 + 0.432)) / 49 + math.log(1 + (u / 18.1) ** 3) / 18.7
    b = 0.564 * ((er - 0.9) / (er + 3)) ** 0.053
    eeff = (er + 1) / 2 + (er - 1) / 2 * (1 + 10 / u) ** (-a * b)
    f = 6 + (2 * math.pi - 6) * math.exp(-((30.666 / u) ** 0.7528))
    z0 = 60 / math.sqrt(eeff) * math.log(f / u + math.sqrt(1 + (2 / u) ** 2))
    return z0, eeff


def diff_microstrip(w, s, h=H):
    z0, _ = microstrip(w, h)
    return 2 * z0 * (1 - 0.48 * math.exp(-0.96 * s / h))


def cpwg(w, g, h=H, er=ER, t=T):
    d = (1.25 * t / math.pi) * (1 + math.log(4 * math.pi * w / t))     # strip-thickness correction
    a, b = w / 2 + d / 2, w / 2 + g - d / 2
    k = a / b; kp = math.sqrt(1 - k * k)
    k1 = math.tanh(math.pi * a / (2 * h)) / math.tanh(math.pi * b / (2 * h)); k1p = math.sqrt(1 - k1 * k1)
    K = lambda m: ellipk(m * m)
    r = K(kp) * K(k1) / (K(k) * K(k1p))
    eeff = (1 + er * r) / (1 + r)
    return 60 * math.pi / math.sqrt(eeff) / (K(k) / K(kp) + K(k1) / K(k1p)), eeff


if __name__ == "__main__":
    w50 = brentq(lambda w: microstrip(w)[0] - 50, 0.05, 2)
    print(f"50R microstrip L1/L2: w = {w50:.3f} mm")
    for g in (0.15, 0.20, 0.25):
        w = brentq(lambda w: cpwg(w, g)[0] - 50, 0.05, 2)
        print(f"50R CPWG gap {g:.2f}: w = {w:.3f} mm  (eeff {cpwg(w, g)[1]:.2f})")
    for s in (0.127, 0.15, 0.20):
        w = brentq(lambda w: diff_microstrip(w, s) - 90, 0.05, 1)
        print(f"90R diff  s={s:.3f}: w = {w:.3f} mm   (Zse {microstrip(w)[0]:.1f})")
    for s in (0.127, 0.15):
        w = brentq(lambda w: diff_microstrip(w, s) - 100, 0.05, 1)
        print(f"100R diff s={s:.3f}: w = {w:.3f} mm")
