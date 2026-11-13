#!/usr/bin/env python3
"""Convert data/microdata_2026.csv to the .asc/.rda pair for the batch flow.

The tauargus batch tools (``tauargus_build_arb`` / ``tauargus_run_arb``)
read the native tau-ARGUS fixed-width format: a ``.asc`` data file plus a
sibling ``.rda`` metadata file. Column types follow the engine convention:
every explanatory variable stays a string (categorical), only the response
variable ``value`` is numeric (ints), as the type inference in
``pytauargus.micro`` requires.

Needs pytauargus, e.g. via uvx:

    uvx --with pytauargus python3 csv_to_asc_rda.py
"""

import csv
from pathlib import Path

from pytauargus.micro import micro_asc_rda

HERE = Path(__file__).resolve().parent
CSV = HERE / "data" / "microdata_2026.csv"
ASC = HERE / "data" / "microdata_2026.asc"
RDA = HERE / "data" / "microdata_2026.rda"


def main():
    cols = {}
    with CSV.open() as f:
        for row in csv.DictReader(f):
            for key, value in row.items():
                cols.setdefault(key, []).append(value)
    cols["value"] = [int(v) for v in cols["value"]]
    res = micro_asc_rda(cols, asc_filename=str(ASC), rda_filename=str(RDA))
    print(f"wrote {ASC}")
    print(f"wrote {RDA}")


if __name__ == "__main__":
    main()
