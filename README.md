# fangstdata-collector

Downloads annual fish landing data (sluttseddel) CSV archives from Fiskeridirektoratet. One ZIP per year, 2007–present.

## Source

Every commercial fish landing in Norway generates a sluttseddel (sales note) filed through one of six regional salgslag. Fiskeridirektoratet publishes the full history as yearly CSV files at `register.fiskeridir.no/uttrekk/fangstdata_{year}.csv.zip`.

Prior years (2007–2022) are frozen. Current + prior year (2024–2025) receive rolling updates as salgslag process late/revised sluttsedler. The collector re-downloads if the remote ETag or Last-Modified changes.

## What's in it

~1 million rows per year, 133 columns, semicolon-delimited, UTF-8. One row = one line item on one sluttseddel (one species × product form × quality grade per landing). A single landing of mixed species produces multiple rows.

**Gotcha**: these are NOT unique landings. A vessel landing 5 species generates 5+ rows for that one delivery. Count `DISTINCT dokumentnummer` for unique sluttsedler, not row count.

## GCS layout

```
gs://sondre_brreg_data/fangstdata/
├── raw/{year}.csv.zip
└── raw/{year}.meta.json    {etag, last_modified, size, downloaded_at}
```

## Schedule

Cloud Run Job `fangstdata-collector`, daily. Checks current + prior year only (~30s). Backfill mode downloads all 18 years (~5 min).

## Downstream

→ fangstdata-parser (reads ZIPs, writes hive-partitioned parquet)
