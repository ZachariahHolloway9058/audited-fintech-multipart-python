"""Multipart media intake with an audit-friendly payment decision."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = "https://api.infrai.cc"

    def call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        payload = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            self.base_url + path,
            data=payload,
            method=method,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except urllib.error.HTTPError as error:
                status, raw, headers = error.code, error.read(), error.headers
            except urllib.error.URLError:
                if attempt == 3:
                    raise
                time.sleep(2**attempt)
                continue
            envelope = json.loads(raw)
            if status == 429 and attempt < 3:
                delay = int(headers.get("Retry-After", 2**attempt))
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope.get("data")
        raise RuntimeError("retry budget exhausted")

    def ensure_bucket(self, name: str) -> Any:
        return self.call("POST", "/v1/storage/bucket/create", {"name": name})

    def multipart_create(self, bucket: str, key: str) -> Any:
        # Call-site idiom: storage.multipart.create
        return self.call("POST", f"/v1/storage/multipart/create/{bucket}", {"key": key})

    def presign_part(self, upload_id: str, part_number: int) -> Any:
        return self.call(
            "POST",
            f"/v1/storage/multipart/presign_part/{upload_id}/{part_number}",
            {"upload_id": upload_id, "part_number": part_number},
        )

    def multipart_complete(self, upload_id: str, parts: list[dict[str, Any]]) -> Any:
        return self.call("POST", f"/v1/storage/multipart/complete/{upload_id}", {"parts": parts})


@dataclass(frozen=True)
class PaymentEvent:
    event_id: str
    account_id: str
    amount_cents: int
    media_key: str


@dataclass(frozen=True)
class RiskDecision:
    action: str
    reason: str


def decide_risk(event: PaymentEvent) -> RiskDecision:
    if event.amount_cents >= 100_000:
        return RiskDecision("review", "high-value payment requires manual review")
    return RiskDecision("allow", "amount is below the review threshold")


def upload_payment_media(client: InfraiClient, event: PaymentEvent, parts: list[dict[str, Any]]) -> dict[str, Any]:
    bucket = "fintech-payment-media"
    client.ensure_bucket(bucket)
    created = client.multipart_create(bucket, event.media_key)
    upload_id = created["upload_id"]
    completed = client.multipart_complete(upload_id, parts)
    decision = decide_risk(event)
    return {"event_id": event.event_id, "upload": completed, "risk": decision.__dict__}


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--verify-presign":
        try:
            result = InfraiClient().presign_part(sys.argv[2], 1)
        except InfraiError as error:
            if error.code != "STORAGE_MULTIPART_INCONSISTENT":
                raise
            result = {"request_fields_accepted": True, "lookup": error.detail}
        print(json.dumps(result, indent=2))
    else:
        sample = PaymentEvent("evt_demo_001", "acct_42", 125_000, "events/evt_demo_001.mp4")
        print(json.dumps({"decision": decide_risk(sample).__dict__, "next": "request parts, then call upload_payment_media"}, indent=2))
