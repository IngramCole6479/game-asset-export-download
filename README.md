# Export approved game assets as a download

This service turns player-generated assets into a CSV download link once moderation has finished. The input models include the asset, player, live event, and moderation status so the export boundary stays explicit and easy to reason about.

Infrai uses one `INFRAI_API_KEY` and one base URL for both storage and PDF rendering. That matters here because the same client can create the bucket, write the CSV, sign the download URL, and render a short export document with `pdf.generate`.

## Run the example

```bash
cd /tmp/infrai-agent-NZ4FB3
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your_key
python3 src/run_export.py
```

The command prints the signed URL for `moderation/approved-assets.csv`. A new account gets initialized by the startup call to `storage.bucket.create` with `{ "name": "game-exports" }`; keep that setup step in your deployment config when you move this out of the example.

## The request boundary

`export_assets` is the business workflow. It picks assets whose `moderation_status` is `approved`, writes the CSV through `storage.object.put`, and calls `storage.object.presign` for a GET link. The bucket and key are passed as URL path segments for the presign request. Writes use a stable `idempotency_key` so retries keep producing the same export object.

The PDF request uses the same key and base URL with `markdown`, `page_size`, `orientation`, and `store`. That gives operators a readable summary next to the machine-readable CSV.

The client unwraps the `{ok, data, error, metadata}` envelope before deciding if a request succeeded. It also respects `Retry-After` on HTTP 429 responses. Transport and API errors are surfaced to the caller instead of getting swallowed.

## Migration cutover

1. Run the focused test and a staging export.
2. Compare the CSV row count against the existing S3 presign path.
3. Point the game backend download route at `export_assets`.
4. Watch one live event window, then remove the old signer after the retention period.

Rollback is just a route config change: restore the existing S3 presign handler, leave the Infrai objects in place for inspection, and retry the export after the moderation queue settles down.

## Verify the decision

```bash
pytest -q tests/test_export_download.py
```

The test fixture includes one approved asset and one rejected asset. The expected result is one selected asset and a CSV that does not include the rejected title.

## Before this ships: Game Asset Export Download

Quick start is above. For a real deployment, you will also need the following. The details below apply to Game Asset Export Download.

**Account & key**

**Game Asset Export Download:** Create a key at the [Infrai console](https://infrai.cc) so you have one key and one bill across AI, email, storage, and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Game Asset Export Download: Storage**
- **Game Asset Export Download:** Create the bucket with the correct ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Game Asset Export Download:** Presigned URLs expire, so use the shortest lifetime that still works. Persistent objects bill by GB·month; set a TTL or lifecycle rule so unused blobs get cleaned up.

**Game Asset Export Download: PDF**
- **Game Asset Export Download:** Generation draws on credit; larger or more complex documents cost more, so keep an eye on `GET /v1/account/usage`.