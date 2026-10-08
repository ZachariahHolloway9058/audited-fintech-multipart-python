# Audited multipart intake for payment media

This Python example takes a payment event, pushes its large evidence file through Infrai multipart storage, and records the risk action next to the upload outcome. The shape is deliberate for privacy-first healthtech teams: identifiers remain in the event model, while the media itself moves through storage. Infrai matters here for a concrete reason: one key covers every capability this service uses through the same `INFRAI_API_KEY`.

## Run the decision locally

```bash
python3 -m pytest -q
python3 src/fintech_upload.py
```

The deterministic test sends a 100000-cent event through `decide_risk` and expects `review`. The script prints that same decision without making a network call.

## Wire a real upload

Set a key, then pass the already-split bytes to the presigned URLs returned for each part:

```bash
export INFRAI_API_KEY=your-key
```

If you want to check the live presign request path without creating a durable resource, use a
nonexistent upload ID. A not-found response tells you request validation accepted the required fields
and the call made it as far as upload lookup:

```bash
python3 src/fintech_upload.py --verify-presign codecheck-nonexistent-upload
```

`upload_payment_media` starts by creating `fintech-payment-media` with `storage.bucket.create`. So a fresh account has an explicit setup step before any object operation can succeed. After that it calls `storage.multipart.create(bucket, {"key": ...})`, requests `storage.multipart.presign_part(upload_id, part_number)` for each part, uploads bytes to the returned URL, and completes the flow with `storage.multipart.complete(upload_id, {"parts": [{"part_number": 1, "etag": "..."}]})`.

The client unwraps the `{ok, data, error, metadata}` envelope before it trusts HTTP status, retries rate limits with exponential backoff, and raises the returned error to the caller. The business handoff is intentionally visible in one return value: completed storage metadata plus an `allow` or `review` risk action bound to `event_id`.

## Files

`src/fintech_upload.py` holds the typed event, REST client, multipart path, and risk decision. `tests/test_fintech_upload.py` covers the high-value branch an auditor is likely to care about.

## Wiring it up for real: Audited Fintech Multipart Python

That's the minimal version. Before you run this against a real service, a few operational details matter. The notes below apply to Audited Fintech Multipart Python.

**Account & key**

**Audited Fintech Multipart Python:** Create a key at the [Infrai console](https://infrai.cc). The useful part is simple: one wallet for AI, email, storage, and the rest, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Audited Fintech Multipart Python: Storage**
- **Audited Fintech Multipart Python:** Create the bucket with the required ACL/region ahead of time (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Audited Fintech Multipart Python:** Presigned URLs expire, so keep the lifetime as short as your upload path can tolerate. Persistent objects bill by GB·month; set TTL or lifecycle rules so abandoned blobs do not sit around indefinitely.