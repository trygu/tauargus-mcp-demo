#!/usr/bin/env python3
"""Generate synthetic vital-events microdata for the tauargus-mcp demo.

Theme: "Levendefodte og dode i norske kommuner, 2026". One row per birth
or per death. The file is event-level only (no person-level data), so it
is privacy-safe by construction.

Columns (data/microdata_2026.csv):
  kommunenummer  4-digit official SSB municipality code
  type           levendefodt (birth) or dod (death), ASCII only
  manndom        K (female) or M (male)
  maned          month, 1-12
  verdi          1 (one record per event)

Deterministic model (random seed 20260):
  births ~ Poisson(population * 0.0105)
  deaths ~ Poisson(population * death_rate), death_rate per municipality
  manndom  K/M; 50/50 in general, 0.52 male share for deaths in the
           small municipalities (mild rural skew)
  maned    uniform 1-12 for births; for deaths, months 1, 2 and 12
           get weight 2 (mild winter bump)

Reference data: kommunenummer and populations are real, from the current
official SSB municipality list (classification 131; populations as of
1 January 2026). All event counts are synthetic. Note: the SSB codes
were renumbered from 1 January 2024 (Oslo 0301, Bergen 4601, Trondheim
5001, Stavanger 1103, Kristiansand 4204); Lenvik was merged into Senja
in 2020 and is no longer a municipality.
"""

import csv
import math
import random
from pathlib import Path

SEED = 20260
BIRTH_RATE = 0.0105

# (kommunenummer, name for the summary, population 1 Jan 2026, death_rate)
# Large, young urban municipalities: death rate 0.085-0.095.
# Small, older rural municipalities: death rate 0.100-0.130.
MUNICIPALITIES = [
    ("0301", "Oslo",         728714, 0.085),
    ("4601", "Bergen",       294860, 0.087),
    ("5001", "Trondheim",    218460, 0.088),
    ("1103", "Stavanger",    151669, 0.090),
    ("4204", "Kristiansand", 119287, 0.095),
    ("1833", "Rana",          25844, 0.100),
    ("1860", "Vestvagoy",     11606, 0.105),
    ("1866", "Hadsel",         8374, 0.110),
    ("5607", "Vadso",          5808, 0.115),
    ("5612", "Kautokeino",     2886, 0.125),
    ("5041", "Snasa",          2141, 0.130),
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
    return "M" if rng.random() < male_share else "K"


def month_birth(rng):
    return rng.randint(1, 12)


def month_death(rng):
    return rng.choices(range(1, 13), weights=DEATH_MONTH_WEIGHTS)[0]


def main():
    rng = random.Random(SEED)
    rows = []
    per_muni = {}
    for code, name, pop, death_rate in MUNICIPALITIES:
        n_births = poisson(rng, pop * BIRTH_RATE)
        n_deaths = poisson(rng, pop * death_rate)
        male_small = DEATH_MALE_SHARE_SMALL if pop < 25000 else 0.5
        for _ in range(n_births):
            rows.append((code, "levendefodt", sex(rng, 0.5), month_birth(rng), 1))
        for _ in range(n_deaths):
            rows.append((code, "dod", sex(rng, male_small), month_death(rng), 1))
        per_muni[code] = (name, n_births, n_deaths)

    rows.sort(key=lambda r: (r[0], r[1], r[3], r[2]))

    out = Path(__file__).resolve().parent / "data" / "microdata_2026.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kommunenummer", "type", "manndom", "maned", "verdi"])
        w.writerows(rows)

    births = sum(v[1] for v in per_muni.values())
    deaths = sum(v[2] for v in per_muni.values())
    print(f"seed={SEED}")
    print(f"wrote {out} ({len(rows)} rows)")
    print(f"total: rows={len(rows)} births={births} deaths={deaths}")
    print("per municipality (code  name               births  deaths):")
    for code, name, pop, _ in MUNICIPALITIES:
        _, b, d = per_muni[code]
        print(f"  {code}  {name:<16} {b:>6}  {d:>6}")


if __name__ == "__main__":
    main()
