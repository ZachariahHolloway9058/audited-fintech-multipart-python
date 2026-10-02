from src.fintech_upload import InfraiClient, PaymentEvent, decide_risk


def test_high_value_payment_is_reviewed():
    event = PaymentEvent("evt_1", "acct_1", 100_000, "events/evt_1.mp4")
    decision = decide_risk(event)
    assert decision.action == "review"
    assert "manual review" in decision.reason


def test_presign_part_sends_required_request_fields():
    client = InfraiClient("test-key")
    calls = []
    client.call = lambda method, path, body=None: calls.append((method, path, body))

    client.presign_part("upload_123", 2)

    assert calls == [
        (
            "POST",
            "/v1/storage/multipart/presign_part/upload_123/2",
            {"upload_id": "upload_123", "part_number": 2},
        )
    ]
