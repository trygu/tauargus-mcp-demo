# tauargus-mcp demo

**Synthetic data - not official statistics.** This repository is a demo
workspace for testing `pytauargus-mcp`, the MCP server and consultant
front-end for the tau-ARGUS statistical disclosure control engine. The
dataset is "levendefodte og dode i norske kommuner, 2026" (live births
and deaths in Norwegian municipalities, 2026). All event counts are
synthetic and deterministic (fixed seed 20260). Only the kommunenummer
codes and the reference populations are real (SSB, 1 January 2026).
Nothing here is official statistics.

## The data

`data/microdata_2026.csv` holds one row per birth or per death, for 11
municipalities.

| Column | Meaning |
| --- | --- |
| `kommunenummer` | 4-digit official SSB municipality code (string) |
| `type` | Event: `levendefodt` (birth) or `dod` (death) |
| `manndom` | Sex of the person born or deceased: `K` or `M` |
| `maned` | Month, 1-12 |
| `verdi` | Numeric response variable, always 1 |

The kommunenummer codes follow the current SSB numbering, which was
renumbered from 1 January 2024 to follow the new county structure
(Oslo is 0301, not the pre-2024 0101). The codes were verified
against the SSB Klass API (classification 131, "Standard for
kommuneinndeling"):
`https://data.ssb.no/api/klass/v1/classifications/131/codesAt?date=2026-06-01`.

The file is event-level only, with no person-level data, so it is
privacy-safe by construction. Summing `verdi` per `kommunenummer` x
`type` gives the births-and-deaths-per-municipality table. The 11
municipalities span a wide population range, from Snasa (about 2,100
people) to Oslo (about 729,000).

Cross-tables that include a `maned` dimension produce small cells in
the small municipalities. In the 4-dimensional cross-table
`kommunenummer` x `type` x `maned` x `manndom`, 89 of the 282
small-municipality cells hold 1-4 events. That is what the disclosure
rules flag: under the default P(25,1) rule, one record contributes at
least 25 percent of such a cell. The corresponding large-municipality
cells run from 35 to 4177 events.

`generate_data.py` (Python 3 standard library, seed 20260) produced the
committed CSV, so the demo works without running the generator.

## Setup

The repo commits `.opencode/opencode.json`, so opening this directory in
OpenCode with `uvx` available connects the `tauargus` MCP server
automatically.

For other MCP clients, use a config like this (Claude Desktop style):

```json
{
  "mcpServers": {
    "tauargus": {
      "command": "uvx",
      "args": ["pytauargus-mcp"]
    }
  }
}
```

## Tools

The server exposes these tools:

- `tauargus_explore` - inspect the microdata: variables, types, ranges
- `tauargus_method_advice` - which protection methods apply to a table,
  their trade-offs, and the recommendation
- `tauargus_assess` - run the safety rules without suppression: which
  cells are sensitive, with values and contributor counts (default rule
  P(25,1): a cell where one record contributes at least 25 percent)
- `tauargus_protect` - build, suppress and write the tables; the
  suppression solve can be slow on large or high-dimensional tables
- `tauargus_audit` - verify the suppressed cells cannot be reconstructed

Cell status legend:

| Code | Meaning |
| --- | --- |
| S | Safe: published as is |
| U | Unsafe (primary): sensitive, value withheld |
| M | Secondary: withheld so a primary cell cannot be reconstructed |
| P | Protected: a publication constraint; not selected for suppression |
| E | Empty: no contributing records |

## Suggested test prompts

- "I have data/microdata_2026.csv. What does it contain?"
- "I want to publish births and deaths per kommunenummer from this
  file. Which protection method should I use?"
- "Assess the table with the standard safety rules and explain in plain
  words why each flagged cell is sensitive."
- "Protect the table, write it, and audit the suppressed cells."
- "Add the maned dimension to the table and protect it again. How do
  the suppressions change?"

## What to expect

- In the plain `kommunenummer` x `type` table, even the smallest cell
  (29 events) is safe, so nothing is suppressed.
- As soon as `maned` (and `manndom`) enter the cross-table, the small
  municipalities yield primary (U) suppressions, and the solver
  withholds neighboring values as secondary (M) suppressions.
- The five large municipalities publish as safe (S) in every
  cross-table.
- `tauargus_audit` confirms that no suppressed value can be
  reconstructed.
