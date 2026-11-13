# tauargus-mcp demo

**Synthetic data - not official statistics.** This repository is a demo
workspace for testing `pytauargus-mcp`, the MCP server and consultant
front-end for the [tau-ARGUS](https://github.com/trygu/tauargus-engine)
statistical disclosure control engine. The
dataset is "levendefodte og dode i norske kommuner, 2026" (live births
and deaths in Norwegian municipalities, 2026). All event counts are
synthetic and deterministic (fixed seed 20260). The municipality codes
and reference populations are real (SSB, 1 January 2026), and the
per-municipality event rates are calibrated to the official SSB 2025
counts (tables 04231 and 08425). Nothing here is official statistics.

## Related projects

This demo only exercises the `pytauargus-mcp` server. The code behind
it lives in the projects below:

- [pytauargus](https://github.com/trygu/pytauargus) - the Python
  package, CLI and TUI for tau-ARGUS, including the `pytauargus-mcp`
  server this demo uses
- [tauargus-engine](https://github.com/trygu/tauargus-engine) - the
  tau-ARGUS statistical disclosure control engine that pytauargus
  wraps (its wheels are built from a pinned engine revision)

## The data

`data/microdata_2026.csv` holds one row per birth or per death, for 12
municipalities. A `.parquet` copy is committed alongside it, because
the MCP server reads `.parquet` paths (or in-memory column dicts)
natively; the CSV is the human-readable source of truth.

| Column | Meaning |
| --- | --- |
| `municipality` | 4-digit official SSB municipality code (string) |
| `event` | Event: `birth` or `death` |
| `sex` | Sex of the person born or deceased: `F` or `M` |
| `month` | Month, 1-12 (string; explanatory variables stay categorical) |
| `value` | Numeric response variable, always 1 |

The municipality codes follow the current SSB numbering, renumbered
from 1 January 2024 to the new county structure (Oslo is 0301, not the
pre-2024 0101); the verification source is in `generate_data.py`.

The file is event-level only, with no person-level data, so it is
privacy-safe by construction. Summing `value` per `municipality` x
`event` gives the births-and-deaths-per-municipality table. The 12
municipalities span a wide population range, from Utsira (219 people)
to Oslo (about 729,000).

The per-municipality event counts are drawn from Poisson models with
those rates, plus a mild male skew in deaths and a winter bump in the
death months; `generate_data.py` carries the full model and the
reference-data provenance.

Cross-tables that include a `month` dimension produce small cells in
the small municipalities. In the 4-dimensional cross-table
`municipality` x `event` x `month` x `sex`, 126 of the 263
non-empty small-municipality cells hold 1-4 events. That is what the
disclosure rules flag: under the default P(25,1) rule, one record
contributes at least 25 percent of such a cell. The corresponding
large-municipality cells run from 35 to 566 events. Utsira, the
smallest municipality, has only 6 non-empty cells in that table - all
of them single events.

`generate_data.py` (Python 3 standard library, seed 20260) produced the
committed CSV, and `csv_to_parquet.py` / `csv_to_asc_rda.py` produced
the committed parquet and `.asc`/`.rda` pair, so the demo works without
running any of them. If you change the generator, run all three to
keep the committed files in sync.

## Which files can you test with?

Why several committed copies? Because the server's input support is
asymmetric: `tauargus_explore` takes a file path only,
`tauargus_assess` / `tauargus_protect` take a `.parquet` path or an
in-memory column dict, and the batch flow takes the native
`.asc`/`.rda` pair. The CSV is the source of truth; the parquet
(3.5 kB) and the `.asc`/`.rda` pair exist so every flow starts
without a conversion step. If you need to convert a new dataset, the
server's `tauargus_to_asc_rda` writes the `.asc`/`.rda` pair from a
`.parquet` path or a column dict.

The microdata tools accept these input forms:

| Input | `tauargus_explore` | `tauargus_assess` / `tauargus_protect` |
| --- | --- | --- |
| `.parquet` file path | yes | yes |
| in-memory dict (column name to list of values) | no | yes |
| `.asc` + sibling `.rda` (native tau-ARGUS fixed-width format) | yes | via `tauargus_build_arb` / `tauargus_run_arb` |
| other tabular sources (CSV, etc.) | convert first: `csv_to_parquet.py` or pass the columns inline as a dict | same |

Column conventions, enforced by the engine:

- Explanatory (dimension) variables must be categorical - keep them
  as strings, e.g. `month` as `"1"`..`"12"`. A numeric explanatory
  variable makes the engine fail with "SetTable failed".
- The response variable must be numeric (here: `value`, always 1).
- `tauargus_explore` on `.asc`/`.rda` reports the engine variable
  types (CATEGORICAL, RESPONSE, WEIGHT, ...); on `.parquet` it
  infers types from the values.
- For the batch flow, `tauargus_build_arb` writes a `.arb` file from
  the `.asc`/`.rda` pair, `tauargus_run_arb` runs it, and
  `tauargus_audit` verifies the result. The repo commits
  `data/microdata_2026.asc` and `data/microdata_2026.rda` (the native
  fixed-width pair), so the batch flow works out of the box.

## The batch (.arb) flow

The batch flow is the same protect + audit cycle, but driven by a
plain-text `.arb` file instead of tool arguments:

1. `tauargus_build_arb` - writes the `.arb` from the `.asc`/`.rda`
   pair (one table per call; it fills in the absolute data-file paths
   itself).
2. `tauargus_run_arb` - runs the batch. The suppression solve happens
   here; it is one blocking call.
3. `tauargus_audit` - verifies the suppressed cells, per table.

A single-table batch for `municipality` x `event` looks like this
(path shown as written, i.e. absolute):

```
<OPENMICRODATA> "/.../data/microdata_2026.asc"
<OPENMETADATA> "/.../data/microdata_2026.rda"
<SPECIFYTABLE> "municipality""event"|"value"||
<SAFETYRULE> P(25,1)
<READMICRODATA>
<SUPPRESS> OPT(1)
<WRITETABLE> (1,4,,"tab1.tab")
```

`tauargus_build_arb` only writes one table per file, but a `.arb` is
just text - for several tables, extend the file by hand. Each table
needs its own `<SAFETYRULE>` line after its `<SPECIFYTABLE>`, and its
own `<SUPPRESS>` (the number in `OPT(n)` is the table number) and
`<WRITETABLE>`. A two-table batch is the file above with the second
table's `<SPECIFYTABLE>` and rule added before `<READMICRODATA>`, and
`<SUPPRESS> OPT(2)` plus `<WRITETABLE> (2,4,,"tab2.tab")` added after
the first table's.

Path conventions inside a `.arb`:

- `<OPENMICRODATA>`/`<OPENMETADATA>` take absolute paths (the build
  tool writes them out absolute).
- `<WRITETABLE>` targets resolve **relative to the .arb file's
  directory**, not the working directory - a `data/`-relative name
  like `data/tab1.tab` next to a `data/`-placed `.arb` would look for
  `data/data/tab1.tab`.

(Verified on the demo data with P(25,1) + OPT suppression.)

- Single-table batch: identical to the direct `protect` flow - Utsira
  birth (2) primary (U), three secondary (M) cells.
- Two-table batch: the 3-dimensional `municipality` x `month` x
  `event` table adds 25 primary (U) and 44 secondary (M)
  suppressions; both tables audit clean.

## Setup

Every example below starts the same server: `uvx pytauargus-mcp`
(a stdio server with no environment variables). All you need
installed is [uv](https://docs.astral.sh/uv/).

### OpenCode

The repo commits `.opencode/opencode.json`, so opening this directory in
OpenCode with `uvx` available connects the `tauargus` MCP server
automatically.

### Claude

**Claude Desktop**: add the block below to
`claude_desktop_config.json`
(`~/Library/Application Support/Claude/claude_desktop_config.json` on
macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows).

**Claude Code**: either run

```sh
claude mcp add tauargus -- uvx pytauargus-mcp
```

or commit a project-scope `.mcp.json` in the repo root (same block;
Claude Code asks you to approve it the first time). Check the
connection with `/mcp` inside a session.

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

### Gemini CLI

Add the same block to `~/.gemini/settings.json` (all projects) or
`.gemini/settings.json` in the repo (this project only). Tools are
exposed as `mcp_tauargus_*`; check the connection with `/mcp`.

### VS Code (GitHub Copilot)

Add to `.vscode/mcp.json` in the workspace (or use *Copilot: Add MCP
Server* from the command palette and enter the command
`uvx pytauargus-mcp`). Note the format difference: VS Code uses
`servers` instead of `mcpServers` and requires `"type": "stdio"`.

```json
{
  "servers": {
    "tauargus": {
      "type": "stdio",
      "command": "uvx",
      "args": ["pytauargus-mcp"]
    }
  }
}
```

Tip: VS Code also reads a portable `.mcp.json` in the repo root with
the `mcpServers` block, so a single committed `.mcp.json` covers both
Claude Code and VS Code.

## Tools

The server exposes these tools:

- `tauargus_version` - the package and engine versions that are running
- `tauargus_explore` - inspect the microdata: variables, types, ranges
- `tauargus_to_asc_rda` - write the `.asc`/`.rda` pair from a
  `.parquet` path or a column dict
- `tauargus_method_advice` - which protection methods apply to a table,
  their trade-offs, and the recommendation
- `tauargus_assess` - run the safety rules without suppression: which
  cells are sensitive, with values and contributor counts (default rule
  P(25,1): a cell where one record contributes at least 25 percent)
- `tauargus_protect` - build, suppress and write the tables; the
  suppression solve can be slow on large or high-dimensional tables
- `tauargus_build_arb` - write a `.arb` batch file from the
  `.asc`/`.rda` pair (one table per call)
- `tauargus_run_arb` - run a `.arb` batch and report the table files
  it writes
- `tauargus_audit` - verify the suppressed cells cannot be
  reconstructed (works on both `protect` workdirs and `.arb` batches)
- `tauargus_report` - write the session up as a markdown protection
  report (internal working document; `public=true` for the redacted
  distribution copy)

Cell status legend:

| Code | Meaning |
| --- | --- |
| S | Safe: published as is |
| U | Unsafe (primary): sensitive, value withheld |
| M | Secondary: withheld so a primary cell cannot be reconstructed |
| P | Protected: a publication constraint; not selected for suppression |
| E | Empty: no contributing records |

## Basis

The method advice, rule meanings and status legend describe standard
statistical disclosure control practice as documented in the legacy
tau-ARGUS 4.1 manual. The method trade-offs follow the overview in
Meindl (2025), *Statistical Disclosure Control. Improving tools and
methods to facilitate the application*, doctoral thesis, Johannes
Kepler University Linz:
<https://epub.jku.at/obvulihs/content/titleinfo/11740128>.

## Suggested test prompts

- "I have data/microdata_2026.parquet. What does it contain?"
- "I want to publish births and deaths per municipality from this
  file. Which protection method should I use?"
- "Assess the table with the standard safety rules and explain in plain
  words why each flagged cell is sensitive."
- "Protect the table, write it, and audit the suppressed cells."
- "Add the month dimension to the table and protect it again. How do
  the suppressions change?"

Variations:

- "Assess the 4-dimensional table with P(80,1) instead of the
  default P(25,1). Which cells does the looser rule let through?"
- "Protect the 4-dimensional table with modular suppression (MOD)
  and compare its suppressions to the default method."
- "Create a batch with two tables: municipality x event, and
  municipality x month x event. Protect both and audit each."
- "A journalist asks for the number of deaths in Snasa in January.
  Given the protected table, is it safe to answer?"

## What to expect

(Verified with the default P(25,1) rule and OPT(1) suppression.)

- In the plain `municipality` x `event` table, only Utsira is flagged:
  its birth cell (2 events) is suppressed as primary (U). The solver
  also withholds three cells as secondary (M) suppressions: Utsira's
  death (4), which would otherwise combine with Utsira's published
  total (6) to reconstruct the withheld birth, and Kautokeino's birth
  (27) and death (24). The other 11 municipalities publish as safe (S).
- In the 4-dimensional cross-table the six smallest municipalities
  (Utsira, Snasa, Kautokeino, Vadso, Hadsel, Vestvagoy) yield 143
  primary (U) and 108 secondary (M) suppressions; Rana is large
  enough to stay safe, as are the five large municipalities in every
  cross-table.
- `tauargus_audit` confirms that no suppressed value can be
  reconstructed (checked for both tables above).
