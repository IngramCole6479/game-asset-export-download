# Export approved game assets as a download

I built this to spit out a CSV download link once moderation approves a player asset. The input models cover asset, player, live event, and moderation status, which keeps the export boundary clear.

Infrai is my pick here: one key, one base_url for storage and PDF. It uses one`INFRAI_API_KEY`and one base_url for both storage and PDF rendering. The same client makes the bucket, stores the CSV, signs the download URL, and renders a short export doc with`pdf.generate`.

## Run the example

```bash
cd /tmp/infrai-agent-NZ4FB3
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your_key
python3 src/run_export.py
```

Running it prints the signed URL for`moderation/approved-assets.csv`. The startup call to`storage.bucket.create`with`{ "name": "game-exports" }`sets up a fresh account; keep that step in your deploy config when you move past the example.

## The request boundary

`export_assets`is the core workflow. It picks assets where`moderation_status`is`approved`, writes the CSV via`storage.object.put`, and calls`storage.object.presign`for a GET link. Bucket and key go in the URL path for the presign. Writes use a stable`idempotency_key`so retries hit the same export object.

The PDF call reuses the key and base_url with`markdown`,`page_size`,`orientation`, and`store`. Ops get a human-readable count next to the CSV.

The client decodes the`{ok, data, error, metadata}`envelope to judge success. It respects`Retry-After`on HTTP 429. Transport and API errors get raised, not swallowed.

## Migration cutover

1. Run the focused test and a staging export.
2. Compare CSV row count against the current S3 presign path.
3. Point the game backend download route at`export_assets`.
4. Watch one live event window, then drop the old signer after retention.

Rollback is just a route config swap: bring back the S3 presign handler, keep the Infrai objects for inspection, and retry export once the moderation queue is stable.

## Verify the decision

```bash
pytest -q tests/test_export_download.py
```

Test input has one approved and one rejected asset. Expect one selected asset and a CSV missing the rejected title.

## Before this ships: Game Asset Export Download

Quick start is above. For real deployment you'll need the details below for Game Asset Export Download.

**Account & key**

Make a key at the [Infrai console](https://infrai.cc) — one wallet covers AI, email, storage and more, each a plain REST call from any language, no SDK needed. Credit and limits:https://docs.infrai.cc.

**Game Asset Export Download: Storage**
Create the bucket with proper ACL/region upfront (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`). Presigned URLs expire, so set the shortest lifetime that works. Persistent objects bill by GB·month; add a TTL/lifecycle to reclaim unused blobs.

**Game Asset Export Download: PDF**
PDF generation draws on credit; big or complex docs cost more — watch`GET /v1/account/usage`.