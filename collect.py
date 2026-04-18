"""Collector for Fiskeridirektoratet fangstdata (sluttseddel + landingsseddel).

Annual zipped CSV files at:
  https://register.fiskeridir.no/uttrekk/fangstdata_{year}.csv.zip

Refresh policy:
  - For each year in YEARS env var (or default range), HEAD the URL
  - If ETag/Last-Modified differs from prior collection meta, re-download
  - Otherwise skip

Prior years (2007-2019) are frozen at source (last touched 2019-12-12).
Recent years (current + previous) get rolling updates from Fiskeridirektoratet
when sluttseddel revisions arrive from the salgslag.

Env vars:
    GCS_BUCKET       Target bucket (default: sondre_brreg_data)
    GCS_PREFIX       Prefix within bucket (default: fangstdata)
    YEARS            CSV of years (default: rolling = current_year and current_year-1)
    RUN_MODE         daily / backfill (default: daily)
                     backfill = ignore ETag check, re-download all
    SCRAPE_DELAY     Seconds between requests (default: 1.0)

GCS layout:
    gs://{bucket}/{prefix}/raw/{year}.csv.zip
    gs://{bucket}/{prefix}/raw/{year}.meta.json    (etag, last-modified, size, downloaded_at)
"""

import io
import json
import os
import sys
import time
import uuid
from datetime import date, datetime, timezone

import requests
from google.cloud import storage


GCS_BUCKET = os.environ.get("GCS_BUCKET", "sondre_brreg_data")
GCS_PREFIX = os.environ.get("GCS_PREFIX", "fangstdata")
RUN_MODE = os.environ.get("RUN_MODE", "daily")
SCRAPE_DELAY = float(os.environ.get("SCRAPE_DELAY", "1.0"))

DEFAULT_FIRST_YEAR = 2007
BASE = "https://register.fiskeridir.no/uttrekk/fangstdata_{year}.csv.zip"


def _resolve_years():
    raw = os.environ.get("YEARS", "").strip()
    if raw:
        return sorted(int(y.strip()) for y in raw.split(",") if y.strip())
    today = date.today()
    if RUN_MODE == "backfill":
        return list(range(DEFAULT_FIRST_YEAR, today.year + 1))
    return [today.year - 1, today.year]


def _read_meta(bucket, year):
    blob = bucket.blob(f"{GCS_PREFIX}/raw/{year}.meta.json")
    if not blob.exists():
        return None
    return json.loads(blob.download_as_text())


def _write_meta(bucket, year, meta):
    blob = bucket.blob(f"{GCS_PREFIX}/raw/{year}.meta.json")
    blob.upload_from_string(json.dumps(meta, indent=2), content_type="application/json")


def _head(url):
    r = requests.head(url, timeout=30, allow_redirects=True)
    r.raise_for_status()
    return {
        "etag": r.headers.get("etag", "").strip('"'),
        "last_modified": r.headers.get("last-modified"),
        "content_length": int(r.headers.get("content-length", "0")),
    }


def _download(url, dst_path):
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(dst_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return os.path.getsize(dst_path)


def main():
    started_at = datetime.now(timezone.utc)
    run_id = str(uuid.uuid4())
    years = _resolve_years()

    print("=" * 60, flush=True)
    print(f"  fangstdata-collector", flush=True)
    print(f"  run_id:   {run_id}", flush=True)
    print(f"  mode:     {RUN_MODE}", flush=True)
    print(f"  years:    {years}", flush=True)
    print(f"  GCS:      gs://{GCS_BUCKET}/{GCS_PREFIX}/raw/", flush=True)
    print("=" * 60, flush=True)

    gcs = storage.Client()
    bucket = gcs.bucket(GCS_BUCKET)

    summary = []
    for year in years:
        url = BASE.format(year=year)
        print(f"\n  --- {year} ---", flush=True)
        head = _head(url)
        print(f"    HEAD: etag={head['etag'][:24]}  size={head['content_length']:,}  modified={head['last_modified']}", flush=True)

        prev_meta = _read_meta(bucket, year)
        if RUN_MODE != "backfill" and prev_meta and prev_meta.get("etag") == head["etag"]:
            print(f"    SKIP: etag unchanged since {prev_meta.get('downloaded_at')}", flush=True)
            summary.append({"year": year, "action": "skip", "size": head["content_length"]})
            continue

        local = f"/tmp/fangstdata_{year}.csv.zip"
        print(f"    DOWNLOAD...", flush=True)
        sz = _download(url, local)
        print(f"    downloaded {sz:,} bytes", flush=True)

        blob = bucket.blob(f"{GCS_PREFIX}/raw/{year}.csv.zip")
        blob.upload_from_filename(local)
        print(f"    uploaded to gs://{GCS_BUCKET}/{blob.name}", flush=True)

        meta = {
            "year": year,
            "url": url,
            "etag": head["etag"],
            "last_modified": head["last_modified"],
            "content_length": head["content_length"],
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "downloaded_by_run_id": run_id,
        }
        _write_meta(bucket, year, meta)
        summary.append({"year": year, "action": "downloaded", "size": sz})

        os.unlink(local)
        time.sleep(SCRAPE_DELAY)

    finished_at = datetime.now(timezone.utc)
    print(f"\n  --- summary ---", flush=True)
    for s in summary:
        print(f"    {s['year']}  {s['action']:<11}  {s['size']:>14,} bytes", flush=True)
    n_downloaded = sum(1 for s in summary if s["action"] == "downloaded")
    n_skipped = sum(1 for s in summary if s["action"] == "skip")
    total_sz = sum(s["size"] for s in summary if s["action"] == "downloaded")
    print(f"\n  downloaded: {n_downloaded}   skipped: {n_skipped}   bytes_in: {total_sz:,}", flush=True)
    print(f"  runtime: {(finished_at - started_at).total_seconds():.1f}s", flush=True)


if __name__ == "__main__":
    main()
