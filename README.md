# fangstdata-collector

Annual collector for Norwegian fish catch and landing data (sluttseddel) from Fiskeridirektoratet. Downloads yearly CSV archives covering every commercial fish landing in Norway back to 2007.

## What is this data?

Every time a fishing vessel delivers its catch to a buyer in Norway, a **sluttseddel** (sales note) is filed through one of six regional fish sales organizations (salgslag). The sluttseddel records: who caught it (vessel, skipper), what they caught (species, weight, quality), how they caught it (gear type), where they caught it (fishing ground), and what it sold for (price per kilo, total value).

This is the **income statement of the sea** — the most granular record of a fishing company's revenue-generating activity that exists outside the company's own books. Fiskeridirektoratet aggregates all sluttsedler into annual bulk downloads.

## Why does a credit analyst care?

Financial statements tell you last year's revenue. Fangstdata tells you **this year's catch so far**, at the level of individual landings:

- **YTD catch vs prior year**: Is the company catching less this season? A 30% drop in mackerel catch through June means the full-year revenue forecast needs revision — visible here 6-12 months before the next finstat.
- **Species concentration**: A company that derives 90% of revenue from one species (e.g., mackerel) is exposed to quota reductions, stock collapses, and price volatility for that species. Fangstdata quantifies this precisely.
- **Gear efficiency**: Catch per landing day (CPUE) measures operational efficiency. A trawler that needs 20 landings to catch what it caught in 15 last year is burning more fuel for less revenue.
- **Landing geography**: Where the vessel delivers reveals its operating range. A vessel that normally delivers in Ålesund but starts delivering in Tromsø may have shifted fishing grounds — a sign the usual grounds are depleted.
- **Crew size**: The `besetning` (crew) field per landing reveals labor costs indirectly. A crew of 8 on a vessel that previously ran with 6 could signal maintenance issues (extra hands for manual work) or quota sharing arrangements.

## Data source

- **URL**: `https://register.fiskeridir.no/uttrekk/fangstdata_{year}.csv.zip`
- **Format**: Semicolon-delimited CSV, UTF-8, inside a ZIP archive
- **Coverage**: 2007–present, one file per year
- **Refresh**: Current year + prior year files update periodically as salgslag revise sluttsedler. Years before that are frozen.
- **Size**: ~60 MB per year compressed, ~1M rows per year, 133 columns

## Collection logic

Daily mode checks ETag/Last-Modified of the current and prior year files. If the remote file changed since our last download, re-fetch. Otherwise skip. Backfill mode downloads all years regardless.

## GCS layout

```
gs://sondre_brreg_data/fangstdata/
├── raw/
│   ├── 2024.csv.zip
│   ├── 2024.meta.json      (etag, last_modified, size, downloaded_at)
│   ├── 2025.csv.zip
│   └── 2025.meta.json
└── parsed/v1/              (written by fangstdata-parser)
```

## Cloud Run

- **Job**: `fangstdata-collector`
- **Schedule**: daily (current + prior year only; backfill run once for 2007-2022)
- **Runtime**: ~30s for a 2-year daily check; ~5 min for full 18-year backfill

## Downstream

→ fangstdata-parser (reads raw ZIPs, writes hive-partitioned parquet)
