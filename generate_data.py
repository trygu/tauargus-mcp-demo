#!/usr/bin/env python3
"""Generate synthetic vital-events microdata for the tauargus-mcp demo.

Theme: "Levendefodte og dode i norske kommuner, 2026". One row per birth
or per death. The file is event-level only (no person-level data), so it
is privacy-safe by construction.

Columns (data/microdata_2026.csv):
  municipality   4-digit official SSB municipality code
  event          birth or death
  sex            F (female) or M (male)
  month          1-12
  value          1 (one record per event)

Deterministic model (random seed 20260):
  births ~ Poisson(population * birth_rate), birth_rate per municipality,
           calibrated to the official SSB 2025 birth counts (table 04231)
  deaths ~ Poisson(population * death_rate), death_rate per municipality,
           calibrated to the official SSB 2025 death counts (table 08425)
  sex      F/M; 50/50 in general, 0.52 male share for deaths in the
           small municipalities (mild rural skew)
  month    uniform 1-12 for births; for deaths, months 1, 2 and 12
           get weight 2 (mild winter bump)

Reference data: municipality codes and populations are real, from the current
official SSB municipality list (classification 131; populations as of
1 January 2026, table 07459). The 12 municipalities span from Utsira (219
people) to Oslo (about 729,000). All event counts are synthetic, but the
per-municipality rates are calibrated to the official 2025 event counts:
births from table 04231, deaths from table 08425. Note: the SSB codes were
renumbered from 1 January
2024 (Oslo 0301, Bergen 4601, Trondheim 5001, Stavanger 1103,
Kristiansand 4204); Lenvik was merged into Senja in 2020 and is no longer
a municipality. Codes verified against the SSB Klass API:
https://data.ssb.no/api/klass/v1/classifications/131/codesAt?date=2026-06-01
"""

import csv
import math
import random
from pathlib import Path

SEED = 20260

# (municipality code, name for the summary, population 1 Jan 2026,
#  birth_rate, death_rate)
# Both rates are calibrated against official SSB statistics: 2025 event
# counts divided by the reference population 1 Jan 2026 (table 07459).
# Births from table 04231 ("Levendefodte, etter kjonn (K)"), deaths from
# table 08425 ("Dode, etter kjonn (K)"). Birth rates run 4.6-12.7 per 1000;
# death rates 10.4-28.0 per 1000 (large, young urban municipalities at the
# low end, small, older rural municipalities at the high end).
MUNICIPALITIES = [
    ("0301", "Oslo",         728714, 0.012744, 0.011069),
    ("4601", "Bergen",       294860, 0.010357, 0.013844),
    ("5001", "Trondheim",    218460, 0.010638, 0.012167),
    ("1103", "Stavanger",    151669, 0.010398, 0.012395),
    ("4204", "Kristiansand", 119287, 0.010177, 0.014603),
    ("1833", "Rana",          25844, 0.008783, 0.021127),
    ("1860", "Vestvagoy",     11606, 0.009823, 0.022402),
    ("1866", "Hadsel",         8374, 0.009076, 0.021495),
    ("5607", "Vadso",          5808, 0.009642, 0.026171),
    ("5612", "Kautokeino",     2886, 0.010395, 0.010395),
    ("5041", "Snasa",          2141, 0.008874, 0.028024),
    ("1151", "Utsira",          219, 0.004566, 0.027397),
]

DEATH_MALE_SHARE_SMALL = 0.52  # small municipalities (population < 25000)
DEATH_MONTH_WEIGHTS = [2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]  # Jan..Dec


def poisson(rng, mean):
    """Poisson draw. Knuth for small means; for large means exp(-mean)
    underflows and the normal approximation (excellent for mean >= 30)
    is used instead."""
    if mean <= 0:
        return 0
    if mean < 30:
        limit = math.exp(-mean)
        k = 0
        p = 1.0
        while True:
            p *= rng.random()
            if p <= limit:
                return k
            k += 1
    return max(0, round(mean + math.sqrt(mean) * rng.gauss(0, 1)))


def sex(rng, male_share):
    return "M" if rng.random() < male_share else "F"


def month_birth(rng):
    return rng.randint(1, 12)


def month_death(rng):
    return rng.choices(range(1, 13), weights=DEATH_MONTH_WEIGHTS)[0]


def main():
    rng = random.Random(SEED)
    rows = []
    per_muni = {}
    for code, name, pop, birth_rate, death_rate in MUNICIPALITIES:
        n_births = poisson(rng, pop * birth_rate)
        n_deaths = poisson(rng, pop * death_rate)
        male_small = DEATH_MALE_SHARE_SMALL if pop < 25000 else 0.5
        for _ in range(n_births):
            rows.append((code, "birth", sex(rng, 0.5), month_birth(rng), 1))
        for _ in range(n_deaths):
            rows.append((code, "death", sex(rng, male_small), month_death(rng), 1))
        per_muni[code] = (name, n_births, n_deaths)

    rows.sort(key=lambda r: (r[0], r[1], r[3], r[2]))

    out = Path(__file__).resolve().parent / "data" / "microdata_2026.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["municipality", "event", "sex", "month", "value"])
        w.writerows(rows)

    births = sum(v[1] for v in per_muni.values())
    deaths = sum(v[2] for v in per_muni.values())
    print(f"seed={SEED}")
    print(f"wrote {out} ({len(rows)} rows)")
    print(f"total: rows={len(rows)} births={births} deaths={deaths}")
    print("per municipality (code  name               births  deaths):")
    for code, name, pop, _, _ in MUNICIPALITIES:
        _, b, d = per_muni[code]
        print(f"  {code}  {name:<16} {b:>6}  {d:>6}")


if __name__ == "__main__":
    main()
