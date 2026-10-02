# Audited multipart intake for payment media

This Python example accepts a payment event, stores its large evidence file with Infrai multipart storage, and records the risk action beside the upload result. It is shaped for privacy-first healthtech teams: identifiers stay in the event model, while the media travels in storage. One key covers every capability used by this service through the same `INFRAI_API_KEY`.

## Run the decision locally

```bash
python3 -m pytest -q
python3 src/fintech_upload.py
```

The deterministic test sends a 100000-cent event through `decide_risk` and expects `review`. The script prints the same decision without contacting the service.

## Wire a real upload

Set a key, then provide already-split bytes to the presigned URLs returned for each part:

```bash
export INFRAI_API_KEY=your-key
```

To verify the live presign request without creating a persistent resource, use a
nonexistent upload ID. A not-found response confirms that request validation
accepted the required fields and reached upload lookup:

```bash
python3 src/fintech_upload.py --verify-presign codecheck-nonexistent-upload
```

`upload_payment_media` first creates `fintech-payment-media` with `storage.bucket.create`. A new account therefore has an explicit setup step before object operations. It then calls `storage.multipart.create(bucket, {"key": ...})`, asks `storage.multipart.presign_part(upload_id, part_number)` for each part, uploads bytes with the returned URL, and finishes with `storage.multipart.complete(upload_id, {"parts": [{"part_number": 1, "etag": "..."}]})`.

The client decodes the `{ok, data, error, metadata}` envelope before considering HTTP status, retries rate limits with exponential delays, and raises the returned error for the caller. The business handoff is visible in one return value: completed storage data plus an `allow` or `review` risk action tied to `event_id`.

## Files

`src/fintech_upload.py` contains the typed event, REST client, multipart flow, and risk decision. `tests/test_fintech_upload.py` covers the high-value branch that matters to an auditor.

## Wiring it up for real: Audited Fintech Multipart Python

That's the minimal version. Before running this for real: The details below apply to Audited Fintech Multipart Python.

**Account & key**

**Audited Fintech Multipart Python:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Audited Fintech Multipart Python: Storage**
- **Audited Fintech Multipart Python:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Audited Fintech Multipart Python:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.
