#!/usr/bin/env python3
"""Convert data/microdata_2026.csv to the .parquet the MCP server reads.

The tauargus tools accept .parquet paths (or in-memory column dicts);
the CSV is the committed, human-readable source of truth. Column types
follow the tau-ARGUS convention: every explanatory variable stays a
string (categorical), only the response variable is numeric.

Needs pyarrow, e.g. via uvx:

    uvx --with pyarrow python3 csv_to_parquet.py
"""

import csv
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
CSV = HERE / "data" / "microdata_2026.csv"
PARQUET = HERE / "data" / "microdata_2026.parquet"


def main():
    cols = {}
    with CSV.open() as f:
        for row in csv.DictReader(f):
            for key, value in row.items():
                cols.setdefault(key, []).append(value)
    cols["value"] = [int(v) for v in cols["value"]]
    table = pa.table(cols)
    pq.write_table(table, PARQUET)
    print(f"wrote {PARQUET} ({table.num_rows} rows)")
    print(f"schema: {table.schema}")


if __name__ == "__main__":
    main()
