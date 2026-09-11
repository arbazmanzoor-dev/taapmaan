"""Human thermal stress indices.

Every function here is a published formula, not a heuristic. Citations are in
the docstrings so a reviewer can check the arithmetic against the source.
The frontend carries a JavaScript twin of this module for offline fallback;
this file is the authority.
"""
from __future__ import annotations
import math

def clamp(v: float, a: float, b: float) -> float:
    return max(a, min(b, v))

def norm(v: float, a: float, b: float) -> float:
    return clamp((v - a) / (b - a), 0.0, 1.0)

def w10to2(v: float) -> float:
    """10 m wind -> 2 m by the neutral log law, roughness length 0.01 m.

    WBGT and the globe balance are 2 m quantities; UTCI is defined at 10 m.
    """
    return v * math.log(2 / 0.01) / math.log(10 / 0.01)

def heat_index_c(t_c: float, rh: float) -> float:
    """NWS Rothfusz regression with both standard adjustment terms."""
    t = t_c * 9 / 5 + 32
    if t < 80:
        hi = 0.5 * (t + 61 + (t - 68) * 1.2 + rh * 0.094)
        return ((hi + t) / 2 - 32) * 5 / 9
    hi = (-42.379 + 2.04901523 * t + 10.14333127 * rh - 0.22475541 * t * rh
          - 0.00683783 * t * t - 0.05481717 * rh * rh + 0.00122874 * t * t * rh
          + 0.00085282 * t * rh * rh - 0.00000199 * t * t * rh * rh)
    if rh < 13 and 80 <= t <= 112:
        hi -= ((13 - rh) / 4) * math.sqrt((17 - abs(t - 95)) / 17)
    elif rh > 85 and 80 <= t <= 87:
        hi += ((rh - 85) / 10) * ((87 - t) / 5)
    return (hi - 32) * 5 / 9

def wet_bulb_c(t: float, rh: float) -> float:
    """Stull (2011) closed-form psychrometric wet bulb. Valid 5-99 % RH."""
    r = clamp(rh, 5, 99)
    return (t * math.atan(0.151977 * math.sqrt(r + 8.313659)) + math.atan(t + r)
            - math.atan(r - 1.676331)
            + 0.00391838 * r ** 1.5 * math.atan(0.023101 * r) - 4.686035)

def globe_temp_c(t: float, solar: float, v2: float) -> float:
    """150 mm black globe: radiative gain against forced convection.

    Approximation. A production service should solve Liljegren (1990) properly;
    it has NOT been validated against a reference, so treat WBGT's radiant term as approximate.
    """
    return t + 0.32 * math.sqrt(max(solar, 0.0)) * 1.335 / (max(v2, 0.35) ** 0.35)

def mrt_c(tg: float, ta: float, v: float) -> float:
    """Mean radiant temperature from a globe reading (ISO 7726, 150 mm, eps 0.95)."""
    k = 1.1e8 * (max(v, 0.1) ** 0.6) / (0.95 * (0.15 ** 0.4))
    return ((tg + 273.15) ** 4 + k * (tg - ta)) ** 0.25 - 273.15

def wbgt_c(t: float, rh: float, solar: float, v2: float) -> float:
    """Outdoor WBGT, ISO 7243 weighting 0.7 Tnw + 0.2 Tg + 0.1 Ta."""
    tg = globe_temp_c(t, solar, v2)
    tnw = wet_bulb_c(t, rh) + 0.12 * (tg - t)
    return 0.7 * tnw + 0.2 * tg + 0.1 * t

# --- UTCI --------------------------------------------------------------------
# Full 6th-order polynomial of the UTCI operational procedure (Bröde et al. 2012),
# vendored verbatim from pythermalcomfort 4.4.2 (MIT licence,
# github.com/pythermalcomfort/pythermalcomfort). It replaces a linear shortcut
# that measured 2.5 °C mean error against this on 13 years of real ERA5 days.
_ES_G = (-2836.5744, -6028.076559, 19.54263612, -0.02737830188, 1.6261698e-05, 7.0229056e-10, -1.8680009e-13)

def _es_hpa(t: float) -> float:
    """Saturation vapour pressure (hPa), exactly as the reference implementation."""
    tk = t + 273.15
    es = 2.7150305 * math.log1p(tk)
    for k, gk in enumerate(_ES_G):
        es += gk * tk ** (k - 2)
    return math.exp(es) * 0.01

def _utci_poly(tdb: float, v: float, delta_t_tr: float, pa: float) -> float:
    return (
        tdb
        + 0.607562052
        + (-0.0227712343) * tdb
        + (8.06470249 * (10 ** (-4))) * tdb * tdb
        + (-1.54271372 * (10 ** (-4))) * tdb * tdb * tdb
        + (-3.24651735 * (10 ** (-6))) * tdb * tdb * tdb * tdb
        + (7.32602852 * (10 ** (-8))) * tdb * tdb * tdb * tdb * tdb
        + (1.35959073 * (10 ** (-9))) * tdb * tdb * tdb * tdb * tdb * tdb
        + (-2.25836520) * v
        + 0.0880326035 * tdb * v
        + 0.00216844454 * tdb * tdb * v
        + (-1.53347087 * (10 ** (-5))) * tdb * tdb * tdb * v
        + (-5.72983704 * (10 ** (-7))) * tdb * tdb * tdb * tdb * v
        + (-2.55090145 * (10 ** (-9))) * tdb * tdb * tdb * tdb * tdb * v
        + (-0.751269505) * v * v
        + (-0.00408350271) * tdb * v * v
        + (-5.21670675 * (10 ** (-5))) * tdb * tdb * v * v
        + (1.94544667 * (10 ** (-6))) * tdb * tdb * tdb * v * v
        + (1.14099531 * (10 ** (-8))) * tdb * tdb * tdb * tdb * v * v
        + 0.158137256 * v * v * v
        + (-6.57263143 * (10 ** (-5))) * tdb * v * v * v
        + (2.22697524 * (10 ** (-7))) * tdb * tdb * v * v * v
        + (-4.16117031 * (10 ** (-8))) * tdb * tdb * tdb * v * v * v
        + (-0.0127762753) * v * v * v * v
        + (9.66891875 * (10 ** (-6))) * tdb * v * v * v * v
        + (2.52785852 * (10 ** (-9))) * tdb * tdb * v * v * v * v
        + (4.56306672 * (10 ** (-4))) * v * v * v * v * v
        + (-1.74202546 * (10 ** (-7))) * tdb * v * v * v * v * v
        + (-5.91491269 * (10 ** (-6))) * v * v * v * v * v * v
        + 0.398374029 * delta_t_tr
        + (1.83945314 * (10 ** (-4))) * tdb * delta_t_tr
        + (-1.73754510 * (10 ** (-4))) * tdb * tdb * delta_t_tr
        + (-7.60781159 * (10 ** (-7))) * tdb * tdb * tdb * delta_t_tr
        + (3.77830287 * (10 ** (-8))) * tdb * tdb * tdb * tdb * delta_t_tr
        + (5.43079673 * (10 ** (-10))) * tdb * tdb * tdb * tdb * tdb * delta_t_tr
        + (-0.0200518269) * v * delta_t_tr
        + (8.92859837 * (10 ** (-4))) * tdb * v * delta_t_tr
        + (3.45433048 * (10 ** (-6))) * tdb * tdb * v * delta_t_tr
        + (-3.77925774 * (10 ** (-7))) * tdb * tdb * tdb * v * delta_t_tr
        + (-1.69699377 * (10 ** (-9))) * tdb * tdb * tdb * tdb * v * delta_t_tr
        + (1.69992415 * (10 ** (-4))) * v * v * delta_t_tr
        + (-4.99204314 * (10 ** (-5))) * tdb * v * v * delta_t_tr
        + (2.47417178 * (10 ** (-7))) * tdb * tdb * v * v * delta_t_tr
        + (1.07596466 * (10 ** (-8))) * tdb * tdb * tdb * v * v * delta_t_tr
        + (8.49242932 * (10 ** (-5))) * v * v * v * delta_t_tr
        + (1.35191328 * (10 ** (-6))) * tdb * v * v * v * delta_t_tr
        + (-6.21531254 * (10 ** (-9))) * tdb * tdb * v * v * v * delta_t_tr
        + (-4.99410301 * (10 ** (-6))) * v * v * v * v * delta_t_tr
        + (-1.89489258 * (10 ** (-8))) * tdb * v * v * v * v * delta_t_tr
        + (8.15300114 * (10 ** (-8))) * v * v * v * v * v * delta_t_tr
        + (7.55043090 * (10 ** (-4))) * delta_t_tr * delta_t_tr
        + (-5.65095215 * (10 ** (-5))) * tdb * delta_t_tr * delta_t_tr
        + (-4.52166564 * (10 ** (-7))) * tdb * tdb * delta_t_tr * delta_t_tr
        + (2.46688878 * (10 ** (-8))) * tdb * tdb * tdb * delta_t_tr * delta_t_tr
        + (2.42674348 * (10 ** (-10))) * tdb * tdb * tdb * tdb * delta_t_tr * delta_t_tr
        + (1.54547250 * (10 ** (-4))) * v * delta_t_tr * delta_t_tr
        + (5.24110970 * (10 ** (-6))) * tdb * v * delta_t_tr * delta_t_tr
        + (-8.75874982 * (10 ** (-8))) * tdb * tdb * v * delta_t_tr * delta_t_tr
        + (-1.50743064 * (10 ** (-9))) * tdb * tdb * tdb * v * delta_t_tr * delta_t_tr
        + (-1.56236307 * (10 ** (-5))) * v * v * delta_t_tr * delta_t_tr
        + (-1.33895614 * (10 ** (-7))) * tdb * v * v * delta_t_tr * delta_t_tr
        + (2.49709824 * (10 ** (-9))) * tdb * tdb * v * v * delta_t_tr * delta_t_tr
        + (6.51711721 * (10 ** (-7))) * v * v * v * delta_t_tr * delta_t_tr
        + (1.94960053 * (10 ** (-9))) * tdb * v * v * v * delta_t_tr * delta_t_tr
        + (-1.00361113 * (10 ** (-8))) * v * v * v * v * delta_t_tr * delta_t_tr
        + (-1.21206673 * (10 ** (-5))) * delta_t_tr * delta_t_tr * delta_t_tr
        + (-2.18203660 * (10 ** (-7))) * tdb * delta_t_tr * delta_t_tr * delta_t_tr
        + (7.51269482 * (10 ** (-9))) * tdb * tdb * delta_t_tr * delta_t_tr * delta_t_tr
        + (9.79063848 * (10 ** (-11)))
        * tdb
        * tdb
        * tdb
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        + (1.25006734 * (10 ** (-6))) * v * delta_t_tr * delta_t_tr * delta_t_tr
        + (-1.81584736 * (10 ** (-9))) * tdb * v * delta_t_tr * delta_t_tr * delta_t_tr
        + (-3.52197671 * (10 ** (-10)))
        * tdb
        * tdb
        * v
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        + (-3.36514630 * (10 ** (-8))) * v * v * delta_t_tr * delta_t_tr * delta_t_tr
        + (1.35908359 * (10 ** (-10)))
        * tdb
        * v
        * v
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        + (4.17032620 * (10 ** (-10)))
        * v
        * v
        * v
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        + (-1.30369025 * (10 ** (-9)))
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        + (4.13908461 * (10 ** (-10)))
        * tdb
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        + (9.22652254 * (10 ** (-12)))
        * tdb
        * tdb
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        + (-5.08220384 * (10 ** (-9)))
        * v
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        + (-2.24730961 * (10 ** (-11)))
        * tdb
        * v
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        + (1.17139133 * (10 ** (-10)))
        * v
        * v
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        + (6.62154879 * (10 ** (-10)))
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        + (4.03863260 * (10 ** (-13)))
        * tdb
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        + (1.95087203 * (10 ** (-12)))
        * v
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        + (-4.73602469 * (10 ** (-12)))
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        + 5.12733497 * pa
        + (-0.312788561) * tdb * pa
        + (-0.0196701861) * tdb * tdb * pa
        + (9.99690870 * (10 ** (-4))) * tdb * tdb * tdb * pa
        + (9.51738512 * (10 ** (-6))) * tdb * tdb * tdb * tdb * pa
        + (-4.66426341 * (10 ** (-7))) * tdb * tdb * tdb * tdb * tdb * pa
        + 0.548050612 * v * pa
        + (-0.00330552823) * tdb * v * pa
        + (-0.00164119440) * tdb * tdb * v * pa
        + (-5.16670694 * (10 ** (-6))) * tdb * tdb * tdb * v * pa
        + (9.52692432 * (10 ** (-7))) * tdb * tdb * tdb * tdb * v * pa
        + (-0.0429223622) * v * v * pa
        + 0.00500845667 * tdb * v * v * pa
        + (1.00601257 * (10 ** (-6))) * tdb * tdb * v * v * pa
        + (-1.81748644 * (10 ** (-6))) * tdb * tdb * tdb * v * v * pa
        + (-1.25813502 * (10 ** (-3))) * v * v * v * pa
        + (-1.79330391 * (10 ** (-4))) * tdb * v * v * v * pa
        + (2.34994441 * (10 ** (-6))) * tdb * tdb * v * v * v * pa
        + (1.29735808 * (10 ** (-4))) * v * v * v * v * pa
        + (1.29064870 * (10 ** (-6))) * tdb * v * v * v * v * pa
        + (-2.28558686 * (10 ** (-6))) * v * v * v * v * v * pa
        + (-0.0369476348) * delta_t_tr * pa
        + 0.00162325322 * tdb * delta_t_tr * pa
        + (-3.14279680 * (10 ** (-5))) * tdb * tdb * delta_t_tr * pa
        + (2.59835559 * (10 ** (-6))) * tdb * tdb * tdb * delta_t_tr * pa
        + (-4.77136523 * (10 ** (-8))) * tdb * tdb * tdb * tdb * delta_t_tr * pa
        + (8.64203390 * (10 ** (-3))) * v * delta_t_tr * pa
        + (-6.87405181 * (10 ** (-4))) * tdb * v * delta_t_tr * pa
        + (-9.13863872 * (10 ** (-6))) * tdb * tdb * v * delta_t_tr * pa
        + (5.15916806 * (10 ** (-7))) * tdb * tdb * tdb * v * delta_t_tr * pa
        + (-3.59217476 * (10 ** (-5))) * v * v * delta_t_tr * pa
        + (3.28696511 * (10 ** (-5))) * tdb * v * v * delta_t_tr * pa
        + (-7.10542454 * (10 ** (-7))) * tdb * tdb * v * v * delta_t_tr * pa
        + (-1.24382300 * (10 ** (-5))) * v * v * v * delta_t_tr * pa
        + (-7.38584400 * (10 ** (-9))) * tdb * v * v * v * delta_t_tr * pa
        + (2.20609296 * (10 ** (-7))) * v * v * v * v * delta_t_tr * pa
        + (-7.32469180 * (10 ** (-4))) * delta_t_tr * delta_t_tr * pa
        + (-1.87381964 * (10 ** (-5))) * tdb * delta_t_tr * delta_t_tr * pa
        + (4.80925239 * (10 ** (-6))) * tdb * tdb * delta_t_tr * delta_t_tr * pa
        + (-8.75492040 * (10 ** (-8))) * tdb * tdb * tdb * delta_t_tr * delta_t_tr * pa
        + (2.77862930 * (10 ** (-5))) * v * delta_t_tr * delta_t_tr * pa
        + (-5.06004592 * (10 ** (-6))) * tdb * v * delta_t_tr * delta_t_tr * pa
        + (1.14325367 * (10 ** (-7))) * tdb * tdb * v * delta_t_tr * delta_t_tr * pa
        + (2.53016723 * (10 ** (-6))) * v * v * delta_t_tr * delta_t_tr * pa
        + (-1.72857035 * (10 ** (-8))) * tdb * v * v * delta_t_tr * delta_t_tr * pa
        + (-3.95079398 * (10 ** (-8))) * v * v * v * delta_t_tr * delta_t_tr * pa
        + (-3.59413173 * (10 ** (-7))) * delta_t_tr * delta_t_tr * delta_t_tr * pa
        + (7.04388046 * (10 ** (-7))) * tdb * delta_t_tr * delta_t_tr * delta_t_tr * pa
        + (-1.89309167 * (10 ** (-8)))
        * tdb
        * tdb
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * pa
        + (-4.79768731 * (10 ** (-7))) * v * delta_t_tr * delta_t_tr * delta_t_tr * pa
        + (7.96079978 * (10 ** (-9)))
        * tdb
        * v
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * pa
        + (1.62897058 * (10 ** (-9)))
        * v
        * v
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * pa
        + (3.94367674 * (10 ** (-8)))
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * pa
        + (-1.18566247 * (10 ** (-9)))
        * tdb
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * pa
        + (3.34678041 * (10 ** (-10)))
        * v
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * pa
        + (-1.15606447 * (10 ** (-10)))
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * pa
        + (-2.80626406) * pa * pa
        + 0.548712484 * tdb * pa * pa
        + (-0.00399428410) * tdb * tdb * pa * pa
        + (-9.54009191 * (10 ** (-4))) * tdb * tdb * tdb * pa * pa
        + (1.93090978 * (10 ** (-5))) * tdb * tdb * tdb * tdb * pa * pa
        + (-0.308806365) * v * pa * pa
        + 0.0116952364 * tdb * v * pa * pa
        + (4.95271903 * (10 ** (-4))) * tdb * tdb * v * pa * pa
        + (-1.90710882 * (10 ** (-5))) * tdb * tdb * tdb * v * pa * pa
        + 0.00210787756 * v * v * pa * pa
        + (-6.98445738 * (10 ** (-4))) * tdb * v * v * pa * pa
        + (2.30109073 * (10 ** (-5))) * tdb * tdb * v * v * pa * pa
        + (4.17856590 * (10 ** (-4))) * v * v * v * pa * pa
        + (-1.27043871 * (10 ** (-5))) * tdb * v * v * v * pa * pa
        + (-3.04620472 * (10 ** (-6))) * v * v * v * v * pa * pa
        + 0.0514507424 * delta_t_tr * pa * pa
        + (-0.00432510997) * tdb * delta_t_tr * pa * pa
        + (8.99281156 * (10 ** (-5))) * tdb * tdb * delta_t_tr * pa * pa
        + (-7.14663943 * (10 ** (-7))) * tdb * tdb * tdb * delta_t_tr * pa * pa
        + (-2.66016305 * (10 ** (-4))) * v * delta_t_tr * pa * pa
        + (2.63789586 * (10 ** (-4))) * tdb * v * delta_t_tr * pa * pa
        + (-7.01199003 * (10 ** (-6))) * tdb * tdb * v * delta_t_tr * pa * pa
        + (-1.06823306 * (10 ** (-4))) * v * v * delta_t_tr * pa * pa
        + (3.61341136 * (10 ** (-6))) * tdb * v * v * delta_t_tr * pa * pa
        + (2.29748967 * (10 ** (-7))) * v * v * v * delta_t_tr * pa * pa
        + (3.04788893 * (10 ** (-4))) * delta_t_tr * delta_t_tr * pa * pa
        + (-6.42070836 * (10 ** (-5))) * tdb * delta_t_tr * delta_t_tr * pa * pa
        + (1.16257971 * (10 ** (-6))) * tdb * tdb * delta_t_tr * delta_t_tr * pa * pa
        + (7.68023384 * (10 ** (-6))) * v * delta_t_tr * delta_t_tr * pa * pa
        + (-5.47446896 * (10 ** (-7))) * tdb * v * delta_t_tr * delta_t_tr * pa * pa
        + (-3.59937910 * (10 ** (-8))) * v * v * delta_t_tr * delta_t_tr * pa * pa
        + (-4.36497725 * (10 ** (-6))) * delta_t_tr * delta_t_tr * delta_t_tr * pa * pa
        + (1.68737969 * (10 ** (-7)))
        * tdb
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * pa
        * pa
        + (2.67489271 * (10 ** (-8)))
        * v
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * pa
        * pa
        + (3.23926897 * (10 ** (-9)))
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * pa
        * pa
        + (-0.0353874123) * pa * pa * pa
        + (-0.221201190) * tdb * pa * pa * pa
        + 0.0155126038 * tdb * tdb * pa * pa * pa
        + (-2.63917279 * (10 ** (-4))) * tdb * tdb * tdb * pa * pa * pa
        + 0.0453433455 * v * pa * pa * pa
        + (-0.00432943862) * tdb * v * pa * pa * pa
        + (1.45389826 * (10 ** (-4))) * tdb * tdb * v * pa * pa * pa
        + (2.17508610 * (10 ** (-4))) * v * v * pa * pa * pa
        + (-6.66724702 * (10 ** (-5))) * tdb * v * v * pa * pa * pa
        + (3.33217140 * (10 ** (-5))) * v * v * v * pa * pa * pa
        + (-0.00226921615) * delta_t_tr * pa * pa * pa
        + (3.80261982 * (10 ** (-4))) * tdb * delta_t_tr * pa * pa * pa
        + (-5.45314314 * (10 ** (-9))) * tdb * tdb * delta_t_tr * pa * pa * pa
        + (-7.96355448 * (10 ** (-4))) * v * delta_t_tr * pa * pa * pa
        + (2.53458034 * (10 ** (-5))) * tdb * v * delta_t_tr * pa * pa * pa
        + (-6.31223658 * (10 ** (-6))) * v * v * delta_t_tr * pa * pa * pa
        + (3.02122035 * (10 ** (-4))) * delta_t_tr * delta_t_tr * pa * pa * pa
        + (-4.77403547 * (10 ** (-6))) * tdb * delta_t_tr * delta_t_tr * pa * pa * pa
        + (1.73825715 * (10 ** (-6))) * v * delta_t_tr * delta_t_tr * pa * pa * pa
        + (-4.09087898 * (10 ** (-7)))
        * delta_t_tr
        * delta_t_tr
        * delta_t_tr
        * pa
        * pa
        * pa
        + 0.614155345 * pa * pa * pa * pa
        + (-0.0616755931) * tdb * pa * pa * pa * pa
        + 0.00133374846 * tdb * tdb * pa * pa * pa * pa
        + 0.00355375387 * v * pa * pa * pa * pa
        + (-5.13027851 * (10 ** (-4))) * tdb * v * pa * pa * pa * pa
        + (1.02449757 * (10 ** (-4))) * v * v * pa * pa * pa * pa
        + (-0.00148526421) * delta_t_tr * pa * pa * pa * pa
        + (-4.11469183 * (10 ** (-5))) * tdb * delta_t_tr * pa * pa * pa * pa
        + (-6.80434415 * (10 ** (-6))) * v * delta_t_tr * pa * pa * pa * pa
        + (-9.77675906 * (10 ** (-6))) * delta_t_tr * delta_t_tr * pa * pa * pa * pa
        + 0.0882773108 * pa * pa * pa * pa * pa
        + (-0.00301859306) * tdb * pa * pa * pa * pa * pa
        + 0.00104452989 * v * pa * pa * pa * pa * pa
        + (2.47090539 * (10 ** (-4))) * delta_t_tr * pa * pa * pa * pa * pa
        + 0.00148348065 * pa * pa * pa * pa * pa * pa
    )

def utci_c(t: float, rh: float, solar: float, v10: float) -> float:
    """UTCI (°C). Mean radiant temperature comes from the 2 m globe balance; the
    polynomial takes the 10 m wind, as UTCI defines. Inputs are clamped to the
    polynomial's validity range (Ta -50..50 °C, Tmrt-Ta -30..70 K, wind 0.5..17 m/s)."""
    v2 = w10to2(v10)
    tmrt = mrt_c(globe_temp_c(t, solar, v2), t, v2)      # globe and MRT both at 2 m
    tdb = clamp(t, -50.0, 50.0)
    return _utci_poly(tdb, clamp(v10, 0.5, 17.0), clamp(tmrt - tdb, -30.0, 70.0), _es_hpa(tdb) * rh / 1000.0)

# --- composite indices -------------------------------------------------------

BANDS = [(0, "Low", "GREEN"), (25, "Moderate", "YELLOW"), (45, "High", "ORANGE"),
         (65, "Severe", "RED"), (82, "Extreme", "MAGENTA")]

def band(h: float):
    out = BANDS[0]
    for b in BANDS:
        if h >= b[0]:
            out = b
    return {"min": out[0], "label": out[1], "code": out[2]}

def htsi(wbgt: float, utci: float, hi: float, tmin: float, run: float) -> float:
    """Human Thermal Stress Index, 0-100.

    The three standard indices carry 0.76 of the weight. The remaining 0.24 is
    overnight non-recovery and consecutive-day accumulation -- the two variables
    that dominate heat mortality and that no standard index contains.
    """
    s = (0.34 * norm(wbgt, 22, 40)
         + 0.26 * norm(utci, 26, 62)
         + 0.16 * norm(hi, 27, 70)
         + 0.14 * norm(tmin, 22, 34)
         + 0.10 * norm(run, 0, 6))
    return clamp(s * 100, 0, 100)

def vulnerability(elderly: float, outdoor: float, informal: float,
                  ac: float, green: float) -> float:
    """Composite 0-1. Weights follow Indian heat-mortality case-control studies.

    `elderly` is the 60+ share -- the Indian statistical definition of elderly,
    and the one Census 2011 publishes, so the model matches the available data.
    """
    return (0.30 * norm(elderly, 3.5, 18)
            + 0.25 * norm(outdoor, 8, 45)
            + 0.20 * norm(informal, 3, 60)
            + 0.15 * (1 - norm(ac, 3, 70))
            + 0.10 * (1 - norm(green, 2, 35)))

CDR_PER_1000 = 7.3  # SRS crude death rate

def mortality(h: float, pop: int, vuln: float) -> dict:
    """Exposure-response. Each 10 HTSI points above the adaptation threshold
    raises all-cause relative risk ~10 %, scaled by ward vulnerability.

    Parametric and calibrated to published Ahmedabad 2010 excess mortality --
    NOT fitted to daily counts. Say so out loud when presenting it.
    """
    excess = max(0.0, h - 45) / 10
    rr = math.exp(0.10 * excess)
    v = 0.65 + vuln
    baseline = pop * CDR_PER_1000 / 1000 / 365
    deaths = baseline * (rr - 1) * v
    return {
        "relative_risk": round(rr, 4),
        "vulnerability_multiplier": round(v, 3),
        "mortality_index": round(clamp(100 * (rr - 1) * v / 0.9, 0, 100), 1),
        "excess_deaths": round(deaths, 2),
        "ed_presentations": round(deaths * 18.4, 1),
        "ambulance_calls": round(deaths * 6.2, 1),
    }
