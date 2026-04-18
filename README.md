# fangstdata-collector

Annual zipped CSV collector for Fiskeridirektoratet `landings- og sluttseddelregisteret` (fangstdata seddel koblet med fartøydata).

## Source

`https://register.fiskeridir.no/uttrekk/fangstdata_{year}.csv.zip`
- Open, no auth, NLOD license
- 133 columns, semicolon-separated, UTF-8
- Years 2007–current available
- ~50 MB zipped per year, ~425 MB unzipped
- Verdi columns (`Beløp for fisker`, `Beløp for kjøper`, `Fangstverdi`) lag 12 months as commercial secret

## Refresh policy

Daily mode: HEAD-then-conditional-GET on current year and previous year. Skip if ETag unchanged.

Backfill mode: `RUN_MODE=backfill YEARS=` triggers full re-download of all years 2007 to current.

Frozen years 2007–2019 last touched by FDIR on 2019-12-12. 2020 last updated 2024-12-04. 2023+ updates rolling as salgslag deliver sluttseddel revisions.

## GCS layout

```
gs://sondre_brreg_data/fangstdata/raw/
  {year}.csv.zip
  {year}.meta.json   (etag, last-modified, downloaded_at)
```

## Schedule

`0 8 * * 1` Europe/Oslo (Mondays) — incremental check on rolling years.
